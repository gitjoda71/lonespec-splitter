"""Genererar 3 syntetiska test-PDF:er som efterliknar svenska lönespecar.

Kör:
    python tests/fixtures/generate_fixtures.py

Output:
    tests/fixtures/fixture_visma_3personer.pdf
    tests/fixtures/fixture_hogia_2personer_2sidor.pdf
    tests/fixtures/fixture_okant_format.pdf

Allt innehåll är fiktivt. Personnumren är ogiltiga (alltid 0000 som suffix).
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent
OUT_VISMA = HERE / "fixture_visma_3personer.pdf"
OUT_HOGIA = HERE / "fixture_hogia_2personer_2sidor.pdf"
OUT_OKANT = HERE / "fixture_okant_format.pdf"

# (förnamn, efternamn, personnummer-prefix, datum YYYY-MM-DD)
VISMA_PERSONER = [
    ("Anna",   "Andersson",   "19850517", "2026-04-25"),
    ("Björn",  "Bergström",   "19790203", "2026-04-25"),
    ("Cecilia","Östlund",     "19920811", "2026-04-25"),
]

HOGIA_PERSONER = [
    ("Daniel", "Dahlqvist",  "19880601", "2026-04-25"),
    ("Elin",   "Ekström",    "19950322", "2026-04-25"),
]


def _draw_visma_page(c: canvas.Canvas, person: tuple[str, str, str, str]) -> None:
    first, last, pnr_prefix, datum = person
    pnr = f"{pnr_prefix}-0000"

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 800, "VISMA Lönespecifikation")
    c.setFont("Helvetica", 10)
    c.drawString(50, 780, "Företaget AB    Org.nr 556000-0000")

    # Mottagar-block (typiskt Visma: namn över personnummer)
    c.setFont("Helvetica", 11)
    c.drawString(50, 740, f"{first} {last}")
    c.drawString(50, 725, f"{pnr}")
    c.drawString(50, 710, "Storgatan 1, 111 11 Stockholm")

    # Datum-block (Utbetalningsdatum)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(350, 740, f"Utbetalningsdatum: {datum}")
    c.setFont("Helvetica", 10)
    c.drawString(350, 725, "Period: 2026-04-01 – 2026-04-30")

    # Tabell-liknande rader
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, 660, "Beskrivning")
    c.drawString(300, 660, "Antal")
    c.drawString(380, 660, "À-pris")
    c.drawString(460, 660, "Belopp")
    c.line(50, 655, 540, 655)

    c.setFont("Helvetica", 10)
    rows = [
        ("Månadslön", "1", "32 000", "32 000"),
        ("OB-tillägg", "8", "150",    "1 200"),
        ("Skatt",      "",  "",       "-9 600"),
    ]
    y = 640
    for r in rows:
        for x, val in zip([50, 300, 380, 460], r):
            c.drawString(x, y, val)
        y -= 18

    c.setFont("Helvetica-Bold", 11)
    c.drawString(380, 580, "Att utbetala:")
    c.drawString(460, 580, "23 600 SEK")

    c.setFont("Helvetica", 8)
    c.drawString(50, 50, "Sida 1 av 1")


def _draw_hogia_page(
    c: canvas.Canvas,
    person: tuple[str, str, str, str],
    page_no: int,
    total_pages: int,
) -> None:
    first, last, pnr_prefix, datum = person
    pnr = f"{pnr_prefix}-0000"

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 800, "Hogia LöneAvi")
    c.setFont("Helvetica", 10)
    c.drawString(50, 780, "Exempelbolaget AB")

    # Hogia-mönster: keyword "Anställd:" på första sidan
    if page_no == 1:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, 740, f"Anställd: {first} {last}")
        c.setFont("Helvetica", 10)
        c.drawString(50, 725, f"Personnummer: {pnr}")
        c.drawString(50, 710, "Avdelning: Administration")

        c.setFont("Helvetica-Bold", 10)
        c.drawString(350, 740, f"Lönedatum: {datum}")
        c.drawString(350, 725, "Period: april 2026")

        c.setFont("Helvetica", 10)
        c.drawString(50, 660, "Sida 1: Sammanställning av månaden.")
        c.drawString(50, 640, "Detaljer på sida 2.")
    else:
        # Sida 2 — fortsättning. Personnumret upprepas (typiskt Hogia).
        c.setFont("Helvetica", 10)
        c.drawString(50, 740, f"{first} {last}")
        c.drawString(50, 725, f"Personnummer: {pnr}")

        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, 690, "Detaljerad löneberäkning")
        c.setFont("Helvetica", 10)
        c.drawString(50, 670, "Bruttolön: 35 000 SEK")
        c.drawString(50, 655, "Skatt: -10 200 SEK")
        c.drawString(50, 640, "Att utbetala: 24 800 SEK")

    c.setFont("Helvetica", 8)
    c.drawString(50, 50, f"Sida {page_no} av {total_pages}")


def _draw_okant_page(c: canvas.Canvas) -> None:
    """En enkel pseudo-spec utan keywords och med datum i 'D månad YYYY'-format."""
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "Lönespecifikation")
    c.setFont("Helvetica", 11)
    c.drawString(50, 770, "Filip Forsberg")
    c.drawString(50, 755, "19770909-0000")
    c.drawString(50, 720, "Utbetalas 25 april 2026.")

    c.setFont("Helvetica", 10)
    c.drawString(50, 670, "Bruttolön ............ 28 000 SEK")
    c.drawString(50, 655, "Skatt ................ -7 800 SEK")
    c.drawString(50, 640, "Netto ................ 20 200 SEK")


def build_visma() -> None:
    c = canvas.Canvas(str(OUT_VISMA), pagesize=A4)
    for person in VISMA_PERSONER:
        _draw_visma_page(c, person)
        c.showPage()
    c.save()
    print(f"  Skrev {OUT_VISMA.name}")


def build_hogia() -> None:
    c = canvas.Canvas(str(OUT_HOGIA), pagesize=A4)
    for person in HOGIA_PERSONER:
        for p in (1, 2):
            _draw_hogia_page(c, person, p, 2)
            c.showPage()
    c.save()
    print(f"  Skrev {OUT_HOGIA.name}")


def build_okant() -> None:
    c = canvas.Canvas(str(OUT_OKANT), pagesize=A4)
    _draw_okant_page(c)
    c.showPage()
    c.save()
    print(f"  Skrev {OUT_OKANT.name}")


def main() -> None:
    print("Genererar fixtures …")
    build_visma()
    build_hogia()
    build_okant()
    print("Klart.")


if __name__ == "__main__":
    main()
