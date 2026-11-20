from pathlib import Path

import pytest
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
if FONT.exists():
    pdfmetrics.registerFont(TTFont("FixtureTR", str(FONT)))


@pytest.fixture
def make_pdf(tmp_path):
    def make(pages=None, size=(595, 842), encrypted=False, name="fixture.pdf"):
        target = tmp_path / name
        c = canvas.Canvas(str(target), pagesize=size, encrypt="secret" if encrypted else None)
        for text in pages or ["Atlas A1 ağırlık 8 kg. Batarya süresi 9 saat."]:
            c.setFont("FixtureTR" if FONT.exists() else "Helvetica", 12)
            for row, line in enumerate(text.split("\n")):
                c.drawString(45, size[1] - 70 - row * 22, line)
            c.showPage()
        c.save()
        return target

    return make
