"""Bounded PDF ingestion and evidence rendering. Documents live only in memory."""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import subprocess
import sys
import threading
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageDraw

MAX_BYTES = 10 * 1024 * 1024
PDF_LOCK = threading.RLock()  # PDFium does not support concurrent calls.


@dataclass(frozen=True)
class Page:
    number: int
    text: str
    width: float
    height: float
    words: tuple[dict, ...]


@dataclass(frozen=True)
class Document:
    name: str
    data: bytes
    sha256: str
    pages: tuple[Page, ...]
    skipped_pages: tuple[int, ...]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(str.maketrans({"İ": "i", "I": "ı"})).lower()).strip()


def read_document(path: str | Path) -> Document:
    if not path:
        raise ValueError("Upload a PDF to get started.")
    source = Path(path)
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise ValueError("Upload a valid PDF file.")
    if source.stat().st_size > MAX_BYTES:
        raise ValueError("The PDF must be 10 MB or smaller.")
    with source.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("The PDF must be 10 MB or smaller.")
    if not data.startswith(b"%PDF-"):
        raise ValueError("The file is not a valid PDF.")
    # PDF content is compressed and may expand far beyond the upload-byte cap.
    # Never build its layout in the long-lived model/server process.
    try:
        with PDF_LOCK:
            result = subprocess.run(
                [sys.executable, "-m", "evidencedoc.pdf_worker"],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=12,
                cwd=Path(__file__).resolve().parents[1],
                check=False,
            )
        if result.returncode != 0:
            raise ValueError("The PDF could not be read within the processing limits.")
        payload = json.loads(result.stdout)
        if "error" in payload:
            raise ValueError(payload["error"])
        pages = tuple(Page(**{**item, "words": tuple(item["words"])}) for item in payload["pages"])
        return Document(
            source.name,
            data,
            hashlib.sha256(data).hexdigest(),
            pages,
            tuple(payload["skipped_pages"]),
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("PDF processing timed out. Try a smaller document.") from exc


def extract_pages(data: bytes) -> tuple[list[Page], tuple[int, ...]]:
    """Worker-only parser; its caller must impose process memory/CPU limits."""
    try:
        with PDF_LOCK, pdfium.PdfDocument(data) as pdf:
            if not 1 <= len(pdf) <= 10:
                raise ValueError("The PDF must contain 1–10 pages.")
            for i in range(len(pdf)):
                with closing(pdf[i]) as page:
                    media = page.get_mediabox()
                    crop = page.get_cropbox()
                    if (
                        page.get_rotation() != 0
                        or abs(media[0]) > 0.01
                        or abs(media[1]) > 0.01
                        or any(abs(a - b) > 0.01 for a, b in zip(media, crop))
                    ):
                        raise ValueError(
                            "Cropped or rotated PDF pages are not supported in this release."
                        )
                    width, height = page.get_size()
                    if not all(math.isfinite(v) and 1 <= v <= 3000 for v in (width, height)):
                        raise ValueError("The PDF page dimensions exceed the supported limit.")
        pages, total_characters = [], 0
        with PDF_LOCK, pdfplumber.open(io.BytesIO(data)) as pdf:
            if not pdf.doc.is_extractable:
                raise ValueError("This PDF does not permit text extraction.")
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if len(text) > 20000:
                    raise ValueError("Each page may contain up to 20,000 extracted characters.")
                total_characters += len(text)
                if total_characters > 100000:
                    raise ValueError("The PDF may contain up to 100,000 extracted characters.")
                words = tuple(page.extract_words())
                pages.append(Page(i + 1, text, page.width, page.height, words))
                page.close()
        skipped = tuple(p.number for p in pages if not p.text.strip())
        if len(skipped) == len(pages):
            raise ValueError(
                "No text layer was found. Scanned PDFs require OCR and are not supported in this release."
            )
        return pages, skipped
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "The PDF could not be read. It may be damaged or password-protected."
        ) from exc


def quote_boxes(page: Page, quote: str) -> list[tuple[float, float, float, float]]:
    """Find a quote in reading-order words; boxes are PDF top-left coordinates."""
    needle = normalize(quote)
    if not needle:
        return []
    parts = [normalize(w["text"]) for w in page.words]
    joined = " ".join(parts)
    start = joined.find(needle)
    if start < 0:
        return []
    end, offset, boxes = start + len(needle), 0, []
    for word, part in zip(page.words, parts):
        if offset < end and offset + len(part) > start:
            boxes.append((word["x0"], word["top"], word["x1"], word["bottom"]))
        offset += len(part) + 1
    return boxes


def render_page(document: Document, page_number: int, quote: str = "") -> Image.Image:
    if not isinstance(page_number, int) or not 1 <= page_number <= len(document.pages):
        raise ValueError("Invalid page number.")
    info = document.pages[page_number - 1]
    scale = min(1.8, 1200 / max(info.width, info.height))
    with PDF_LOCK, pdfium.PdfDocument(document.data) as pdf, closing(pdf[page_number - 1]) as page:
        bitmap = page.render(scale=scale)
        try:
            image = bitmap.to_pil().convert("RGB").copy()
        finally:
            bitmap.close()
    overlay = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(overlay)
    for box in quote_boxes(info, quote):
        draw.rectangle(tuple(v * scale for v in box), fill=(255, 209, 62, 100))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
