"""Generate the original fictional English development document (CC0 data)."""

import argparse
import base64
import hashlib
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]


def create_examples(output: Path | None = None, *, regenerate: bool = False):
    output = output or ROOT / "examples/technical-catalog.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    fixture = ROOT / "examples/technical-catalog.fixture.json"
    if not regenerate and fixture.exists():
        payload = json.loads(fixture.read_text())
        data = base64.b64decode(payload["pdf_base64"], validate=True)
        if hashlib.sha256(data).hexdigest() != payload["sha256"]:
            raise ValueError("The sample fixture failed its integrity check.")
        output.write_bytes(data)
        return output
    import reportlab

    candidate = Path(reportlab.__file__).parent / "fonts/Vera.ttf"
    pdfmetrics.registerFont(TTFont("CatalogueTR", str(candidate)))
    c = canvas.Canvas(str(output), pagesize=(595, 842), invariant=1)
    c.setTitle("EvidenceDoc - Fictional Technical Catalogue and Test Report")
    c.setAuthor("EvidenceDoc project")

    def text(x, y, line, size=11, color="#142334"):
        c.setFillColor(colors.HexColor(color))
        c.setFont("CatalogueTR", size)
        c.drawString(x, y, line)

    def header(number, title):
        text(42, 794, "EVIDENCEDOC  /  DEVELOPMENT FIXTURE", 10, "#40648e")
        text(42, 755, title, 20)
        c.setStrokeColor(colors.HexColor("#d7dfe8"))
        c.line(42, 735, 553, 735)
        text(42, 34, "Fictional data - not a real product or laboratory result.", 8)
        text(520, 34, f"{number} / 3", 9)

    header(1, "Portable measurement stations")
    text(42, 705, "The table compares the specifications of three fictional models.")
    columns = [42, 177, 285, 420]
    rows = [
        ["Specification", "Atlas A1", "Bora B2", "Ceren C3"],
        ["Weight", "8 kg", "12 kg", "6 kg"],
        ["Battery life", "9 hours", "12 hours", "5 hours"],
        ["Full charge time", "2 hours", "3 hours", "1.5 hours"],
        ["Protection rating", "IP54", "IP65", "IP44"],
        ["Warranty period", "24 months", "36 months", "24 months"],
        ["Operating temperature", "0–40 °C", "-10–50 °C", "5–35 °C"],
    ]
    for ri, row in enumerate(rows):
        y = 652 - ri * 43
        if ri == 0:
            c.setFillColor(colors.HexColor("#edf2f7"))
            c.rect(36, y - 14, 522, 39, fill=1, stroke=0)
        for x, value in zip(columns, row):
            text(x, y, value, 9)
        c.setStrokeColor(colors.HexColor("#d7dfe8"))
        c.line(36, y - 17, 558, y - 17)
    text(42, 310, "Selection notes", 14)
    text(42, 282, "Atlas A1 is designed for lightweight field use.")
    text(42, 260, "Bora B2 offers longer operation and a higher protection rating.")
    text(42, 238, "Ceren C3 is designed for short indoor measurements.")
    c.showPage()

    header(2, "Atlas A1 power test")
    text(42, 705, "Figure 1. Average power consumption by operating mode", 12)
    for i, (label, value) in enumerate(
        [("Idle", 18), ("Measurement", 30), ("Intensive processing", 45)]
    ):
        y = 620 - i * 100
        text(42, y + 10, label)
        c.setFillColor(colors.HexColor(["#9db4d0", "#527dae", "#214e80"][i]))
        c.rect(165, y, value * 6, 33, fill=1, stroke=0)
        text(172 + value * 6, y + 10, f"{value} W")
    text(42, 330, "Test conditions", 14)
    text(42, 300, "Tests were conducted at an ambient temperature of 23 °C.")
    text(42, 278, "Each operating mode was measured for 60 minutes.")
    text(42, 256, "The sample size was five devices per mode.")
    text(42, 234, "This chart shows only the fictional Atlas A1 test.")
    c.showPage()

    header(3, "Maintenance and operating limits")
    for i, line in enumerate(
        [
            "The calibration interval is 12 months for all models.",
            "The Atlas A1 storage temperature range is -20–60 °C.",
            "Use a dry microfiber cloth for cleaning.",
            "The warranty does not cover damage from full liquid immersion.",
            "The battery must be replaced by an authorized service provider.",
            "This document does not provide pricing, camera or wireless specifications.",
        ]
    ):
        text(42, 692 - i * 39, line, 9)
    c.save()
    return output


QUESTIONS = [
    ("t01", "How much does Atlas A1 weigh?", ["8"], [1], "table"),
    ("t02", "How many hours of battery life does Bora B2 provide?", ["12"], [1], "table"),
    ("t03", "How long does Ceren C3 take to fully charge?", ["1.5"], [1], "table"),
    (
        "t04",
        "Which model weighs less than 10 kg and provides at least 8 hours of battery life?",
        ["Atlas A1"],
        [1],
        "comparison",
    ),
    ("t05", "What is the protection rating of Bora B2?", ["IP65"], [1], "table"),
    ("t06", "How many months is the Atlas A1 warranty?", ["24"], [1], "table"),
    ("t07", "Which model has the longest warranty?", ["Bora B2"], [1], "comparison"),
    ("t08", "How much does Ceren C3 weigh?", ["6"], [1], "table"),
    ("t09", "What is the full charge time of Atlas A1?", ["2"], [1], "table"),
    ("t10", "What is the minimum operating temperature of Bora B2?", ["-10"], [1], "table"),
    ("g01", "What is the average power consumption of Atlas A1 when idle?", ["18"], [2], "chart"),
    (
        "g02",
        "What is the average power consumption in intensive processing mode?",
        ["45"],
        [2],
        "chart",
    ),
    (
        "g03",
        "What is the power difference between measurement and idle modes in watts?",
        ["12"],
        [2],
        "chart-reasoning",
    ),
    ("g04", "What was the ambient temperature during the power tests?", ["23"], [2], "text"),
    ("m01", "What is the calibration interval in months?", ["12"], [3], "text"),
    ("m02", "What type of cloth should be used for cleaning?", ["microfiber"], [3], "text"),
    ("u01", "What is the selling price of Atlas A1?", [], [], "unanswerable"),
    ("u02", "What is the camera resolution of Bora B2 in megapixels?", [], [], "unanswerable"),
    ("u03", "What WiFi frequency does Ceren C3 use?", [], [], "unanswerable"),
    ("u04", "What is the quantum processor model number?", [], [], "unanswerable"),
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Rebuild sample layout; changes its hash and requires new evaluation runs",
    )
    args = parser.parse_args()
    print(create_examples(regenerate=args.regenerate))
    target = ROOT / "evaluation/dev.jsonl"
    target.write_text(
        "".join(
            json.dumps(
                {
                    "id": i,
                    "document": "examples/technical-catalog.pdf",
                    "question": q,
                    "accepted_answers": a,
                    "evidence_pages": p,
                    "category": c,
                    "answerable": bool(a),
                },
                ensure_ascii=False,
            )
            + "\n"
            for i, q, a, p, c in QUESTIONS
        )
    )
