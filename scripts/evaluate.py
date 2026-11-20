"""Reproducible local experiment; reference matching is a proxy, not a semantic judge."""

import argparse
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evidencedoc.documents import normalize  # noqa: E402
from evidencedoc.service import answer_document, search_document  # noqa: E402


def contains_reference(answer, alternatives):
    def folded(s):
        return re.sub(r"(?<=\d),(?=\d)", ".", normalize(s))

    numeric = r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?![\d.])"
    for reference in alternatives:
        reference = folded(reference)
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", reference):
            if any(
                Decimal(value) == Decimal(reference)
                for value in re.findall(numeric, folded(answer))
            ):
                return True
        elif re.search(r"(?<!\w)" + re.escape(reference) + r"(?!\w)", folded(answer)):
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", default="", help="Comma-separated case IDs; empty means all 20")
    parser.add_argument("--search-only", action="store_true")
    parser.add_argument("--output", default="artifacts/evaluation.json")
    args = parser.parse_args()
    cases = [json.loads(line) for line in (ROOT / "evaluation/dev.jsonl").read_text().splitlines()]
    selected = set(args.ids.split(",")) if args.ids else set()
    results = []
    for case in cases:
        if selected and case["id"] not in selected:
            continue
        for mode in ["search"] if args.search_only else ["text", "hybrid"]:
            try:
                path = ROOT / case["document"]
                report = (
                    search_document(path, case["question"])
                    if mode == "search"
                    else answer_document(path, case["question"], mode)
                )
                found = {p["page"] for p in report["retrieved_pages"]}
                expected = set(case["evidence_pages"])
                row = {
                    "id": case["id"],
                    "category": case["category"],
                    "mode": mode,
                    "expected_pages": sorted(expected),
                    "accepted_answers": case["accepted_answers"],
                    "retrieval_recall": len(found & expected) / len(expected) if expected else None,
                    "reference_contains_proxy": None
                    if mode == "search"
                    else (
                        bool(contains_reference(report["answer"], case["accepted_answers"]))
                        and report["status"] == "answered"
                        if case["answerable"]
                        else report["status"] in {"abstained", "no_sources"}
                    ),
                    "report": report,
                }
            except Exception as exc:
                row = {"id": case["id"], "mode": mode, "error": str(exc)}
            results.append(row)
            destination = ROOT / args.output
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(
                    {
                        "dataset": "self-authored fictional development set; not an independent benchmark",
                        "model_revision": "89644892e4d85e24eaac8bacfd4f463576704203",
                        "results": results,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            print(
                json.dumps(
                    {k: v for k, v in row.items() if k != "report"}
                    | {
                        "status": row.get("report", {}).get("status"),
                        "seconds": row.get("report", {}).get("elapsed_seconds"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    if any("error" in row for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
