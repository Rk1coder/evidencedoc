import pytest


def test_extracts_turkish_text_and_one_based_pages(make_pdf):
    from evidencedoc.documents import read_document

    doc = read_document(make_pdf(["Ağırlık 8 kg. Çalışma süresi 9 saat.", "Şarj süresi 3 saat."]))
    assert doc.pages[0].number == 1
    assert "Çalışma süresi 9 saat" in doc.pages[0].text
    assert "Şarj süresi" in doc.pages[1].text
    assert len(doc.sha256) == 64


@pytest.mark.parametrize("payload", [b"", b"not a pdf", b"%PDF-1.7\ntruncated"])
def test_rejects_invalid_pdf(tmp_path, payload):
    from evidencedoc.documents import read_document

    p = tmp_path / "bad.pdf"
    p.write_bytes(payload)
    with pytest.raises(ValueError):
        read_document(p)


def test_rejects_file_over_ten_mib_before_reading(tmp_path):
    from evidencedoc.documents import read_document

    p = tmp_path / "large.pdf"
    with p.open("wb") as f:
        f.truncate(10 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="10 MB"):
        read_document(p)


def test_rejects_more_than_ten_pages(make_pdf):
    from evidencedoc.documents import read_document

    with pytest.raises(ValueError, match="10 pages"):
        read_document(make_pdf(["page"] * 11))


def test_rejects_encryption_and_scan(make_pdf):
    from evidencedoc.documents import read_document

    with pytest.raises(ValueError):
        read_document(make_pdf(encrypted=True))
    with pytest.raises(ValueError, match="text layer"):
        read_document(make_pdf([" "], name="scan.pdf"))


def test_marks_non_text_pages_as_unsearched(make_pdf):
    from evidencedoc.documents import read_document

    doc = read_document(make_pdf(["Atlas ağırlık 8 kg", " "]))
    assert doc.skipped_pages == (2,)


def test_rejects_huge_page_before_render(make_pdf):
    from evidencedoc.documents import read_document

    with pytest.raises(ValueError, match="dimensions"):
        read_document(make_pdf(size=(20000, 20000)))


def test_render_bounds_and_quote_highlighting(make_pdf):
    from evidencedoc.documents import read_document, render_page

    doc = read_document(make_pdf(["Atlas A1 ağırlık 8 kg. Batarya süresi 9 saat."]))
    image = render_page(doc, 1, "ağırlık 8 kg")
    assert max(image.size) <= 1200
    assert image.mode == "RGB"
    yellow = sum(1 for r, g, b in image.get_flattened_data() if r > 200 and g > 160 and b < 180)
    assert yellow > 50
    with pytest.raises(ValueError):
        render_page(doc, 0)


def test_rejects_crop_and_rotation_before_extraction(make_pdf, tmp_path):
    import pypdfium2 as pdfium

    from evidencedoc.documents import read_document

    original = make_pdf(["Visible text"], size=(500, 500))
    for rotation in (0, 90):
        target = tmp_path / f"geometry-{rotation}.pdf"
        with pdfium.PdfDocument(str(original)) as pdf:
            page = pdf[0]
            if rotation:
                page.set_rotation(rotation)
            else:
                page.set_cropbox(100, 100, 400, 400)
            page.close()
            pdf.save(str(target))
        with pytest.raises(ValueError, match="Cropped|rotated"):
            read_document(target)


def test_compressed_layout_bomb_fails_within_enforced_time(tmp_path):
    """Outer process contains the RED baseline; the app must enforce its own cap."""
    import subprocess
    import sys
    import zlib

    path = tmp_path / "compressed.pdf"
    stream = zlib.compress(b"BT /F1 12 Tf 10 10 Td (x) Tj ET\n" * 1_000_000)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" /Filter /FlateDecode >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n" + b"".join(
        f"{off:010d} 00000 n \n".encode() for off in offsets[1:]
    )
    data += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(data)
    code = """from evidencedoc.documents import read_document
import sys
try:
    read_document(sys.argv[1])
except ValueError:
    print('bounded rejection')
else:
    raise SystemExit('unsafe input accepted')
"""
    import time

    import psutil

    with subprocess.Popen(
        [sys.executable, "-c", code, str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        observer = psutil.Process(process.pid)
        deadline = time.monotonic() + 18
        while process.poll() is None:
            try:
                if observer.memory_info().rss > 256 * 1024 * 1024:
                    process.kill()
                    process.communicate()
                    pytest.fail(
                        "Untrusted PDF layout allocated more than 256 MiB in the app process"
                    )
            except psutil.NoSuchProcess:
                break
            if time.monotonic() > deadline:
                process.kill()
                process.communicate()
                pytest.fail("PDF extraction exceeded its enforced resource/time budget")
            time.sleep(0.02)
        stdout, stderr = process.communicate()
        assert process.returncode == 0, stderr
        assert stdout.strip() == "bounded rejection"
