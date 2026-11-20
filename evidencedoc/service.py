"""Document Q&A orchestration, with an explicit citation-presence gate."""

import json
import re
import time

from evidencedoc.documents import normalize, quote_boxes, read_document, render_page
from evidencedoc.inference import MODEL_ID, MODEL_REVISION, get_generator
from evidencedoc.retrieval import retrieve, validate_question

ABSTENTION = "The retrieved pages do not contain enough evidence to answer this question."


def _prepare(path, question):
    question = validate_question(question)
    document = read_document(path)
    hits = retrieve(document, question)
    report = {
        "schema_version": 1,
        "document": {
            "name": document.name,
            "sha256": document.sha256,
            "page_count": len(document.pages),
            "skipped_pages": list(document.skipped_pages),
        },
        "question": question,
        "retrieval": "bilingual_bm25",
        "retrieved_pages": [
            {
                "page": hit.page,
                "score": hit.score,
                "excerpt": document.pages[hit.page - 1].text[:6000],
                "text_truncated": len(document.pages[hit.page - 1].text) > 6000,
            }
            for hit in hits
        ],
        "answer": ABSTENTION,
        "evidence": [],
        "model_called": False,
        "citation_check": "Exact quote presence only; semantic correctness is not guaranteed.",
    }
    return document, report


def search_document(path, question) -> dict:
    start = time.monotonic()
    _, report = _prepare(path, question)
    report.update(
        mode="search",
        status="sources_only" if report["retrieved_pages"] else "no_sources",
        elapsed_seconds=round(time.monotonic() - start, 3),
    )
    if report["retrieved_pages"]:
        report["answer"] = (
            "Relevant pages were found. Source search does not generate a model answer."
        )
    return report


def parse_output(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw) > 20000:
        raise ValueError("The model output exceeds the supported size.")
    raw = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1)
    data, end = json.JSONDecoder().raw_decode(raw)
    # Qwen sometimes emits one redundant closing quote after the complete object.
    # Accept only that harmless delimiter; the full schema/evidence gate still applies.
    if raw[end:].strip() not in {"", '"'}:
        raise ValueError("Unexpected content outside the JSON object.")
    if not isinstance(data, dict) or not isinstance(data.get("answer"), str):
        raise ValueError("The response is missing its answer text.")
    if type(data.get("abstain")) is not bool or not isinstance(data.get("evidence"), list):
        raise ValueError("The model response does not match the expected schema.")
    if len(data["answer"]) > 2000 or len(data["evidence"]) > 3:
        raise ValueError("The model response exceeds the output limits.")
    return data


def answer_document(path, question, mode="hybrid", generator=None) -> dict:
    start = time.monotonic()
    if mode not in {"hybrid", "text"}:
        raise ValueError("Choose hybrid or text mode.")
    document, report = _prepare(path, question)
    report.update(mode=mode, model=MODEL_ID, model_revision=MODEL_REVISION)
    if not report["retrieved_pages"]:
        report.update(status="no_sources", elapsed_seconds=round(time.monotonic() - start, 3))
        return report
    pages = [{"page": p["page"], "text": p["excerpt"]} for p in report["retrieved_pages"]]
    if mode == "hybrid":
        for page in pages:
            image = render_page(document, page["page"])
            image.thumbnail((512, 512))
            page["image"] = image
    engine = generator if generator is not None else get_generator()
    try:
        raw = engine.generate(question.strip(), pages, mode)
    except Exception as exc:
        raise RuntimeError(
            "The model could not run. Check available memory, model download access, and the server logs."
        ) from exc
    report.update(model_called=True, device=getattr(engine, "device", "unknown"))
    try:
        output = parse_output(raw)
    except (ValueError, TypeError):
        report.update(
            status="invalid_model_output",
            answer="The model did not return valid structured output. No answer was displayed.",
        )
    else:
        if output["abstain"]:
            report["status"] = "abstained"
        else:
            evidence, valid = [], bool(output["evidence"]) and bool(output["answer"].strip())
            selected = {index: page for index, page in enumerate(pages, 1)}
            for item in output["evidence"]:
                if not isinstance(item, dict):
                    valid = False
                    break
                source_id, quote = item.get("source_id"), item.get("quote")
                if (
                    type(source_id) is not int
                    or source_id not in selected
                    or not isinstance(quote, str)
                    or not 6 <= len(quote.strip()) <= 500
                    or normalize(quote) not in normalize(selected[source_id]["text"])
                ):
                    valid = False
                    break
                number = selected[source_id]["page"]
                evidence.append(
                    {
                        "page": number,
                        "quote": quote.strip(),
                        "quote_checked": True,
                        "boxes": quote_boxes(document.pages[number - 1], quote),
                    }
                )
            if valid:
                report.update(status="answered", answer=output["answer"].strip(), evidence=evidence)
            else:
                report.update(
                    status="evidence_rejected",
                    answer="The proposed citation did not match the retrieved PDF text. No answer was displayed.",
                )
    report["elapsed_seconds"] = round(time.monotonic() - start, 3)
    return report
