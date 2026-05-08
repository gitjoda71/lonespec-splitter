"""Kärnan: splittra en samlad PDF + namnge varje del.

Strategi v0.1 (ordnad fallback):
1. Använd "Sida X av Y" / "Sida X (Y)" från sidtexten om det är konsistent.
2. Annars: använd personnummer-sidor som "ankare" — varje ankare = ny grupp.
3. Annars: 1 sida = 1 spec.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .extractor import extract_per_page_text
from .filename import build_filename, unique_path
from .parser import (
    PERSONNUMMER,
    extract,
    extract_page_of_n,
    extract_personnummer_pages,
)

logger = logging.getLogger(__name__)


@dataclass
class GroupResult:
    pages_zero: list[int]
    text: str
    out_path: Path
    first: str | None = None
    last: str | None = None
    date: str | None = None
    name_rule: str | None = None
    date_rule: str | None = None
    fallback_used: bool = False


@dataclass
class SplitResult:
    input_path: Path
    output_dir: Path
    groups: list[GroupResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _group_pages(per_page_text: list[str]) -> list[list[int]]:
    """Returnera lista över grupper, varje grupp är en lista med 0-baserade sid-index."""
    n = len(per_page_text)
    if n == 0:
        return []

    # Strategi 1: "Sida X av Y" — om sida 1 säger "Sida 1 av Y" så bygger vi
    # block om Y sidor i taget och kollar att varje sista sida slutar (Y av Y).
    groups_by_sida_av: list[list[int]] = []
    i = 0
    consistent = True
    while i < n:
        marker = extract_page_of_n(per_page_text[i])
        if not marker or marker[0] != 1:
            consistent = False
            break
        x, y = marker
        end = i + y
        if end > n:
            consistent = False
            break
        # Verifiera att sista sidan i blocket är "Sida Y av Y"
        last_marker = extract_page_of_n(per_page_text[end - 1])
        if not last_marker or last_marker != (y, y):
            consistent = False
            break
        groups_by_sida_av.append(list(range(i, end)))
        i = end
    if consistent and groups_by_sida_av:
        logger.info("Gruppering via 'Sida X av Y': %d grupper", len(groups_by_sida_av))
        return groups_by_sida_av

    # Strategi 2: personnummer-ankare
    pnr_pages = extract_personnummer_pages(per_page_text)
    if pnr_pages and pnr_pages[0] == 0:
        groups_by_pnr: list[list[int]] = []
        for idx, start in enumerate(pnr_pages):
            end = pnr_pages[idx + 1] if idx + 1 < len(pnr_pages) else n
            groups_by_pnr.append(list(range(start, end)))
        logger.info("Gruppering via personnummer-ankare: %d grupper", len(groups_by_pnr))
        return groups_by_pnr

    # Strategi 3: 1 sida = 1 spec
    logger.info("Fallback-gruppering: 1 sida per spec (%d sidor)", n)
    return [[i] for i in range(n)]


def _is_encrypted(pdf_path: Path) -> bool:
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    return reader.is_encrypted


def split_pdf(
    input_pdf: Path,
    output_dir: Path,
    *,
    use_ocr: bool = False,
) -> SplitResult:
    """Huvudflöde."""
    input_pdf = Path(input_pdf)
    output_dir = Path(output_dir)

    if not input_pdf.is_file():
        raise FileNotFoundError(f"Indata-PDF saknas: {input_pdf}")
    output_dir.mkdir(parents=True, exist_ok=True)

    if _is_encrypted(input_pdf):
        raise PermissionError("PDF:en är lösenordsskyddad — lås upp den först.")

    result = SplitResult(input_path=input_pdf, output_dir=output_dir)

    # 1. Extrahera text per sida
    per_page_text = extract_per_page_text(input_pdf)
    n_pages = len(per_page_text)

    # 2. OCR-fallback för sidor utan text
    if use_ocr:
        from .ocr import is_available, ocr_page
        if is_available():
            for i, t in enumerate(per_page_text):
                if not t.strip():
                    logger.info("OCR sida %d", i + 1)
                    per_page_text[i] = ocr_page(input_pdf, i)
        else:
            result.warnings.append("OCR begärd men Tesseract saknas — fortsätter utan.")

    # 3. Gruppera sidor
    groups = _group_pages(per_page_text)

    # 4. För varje grupp: extrahera namn/datum, bygg filnamn, skriv ut
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(str(input_pdf))

    for group_pages in groups:
        text = "\n".join(per_page_text[p] for p in group_pages)
        ex = extract(text)

        if not (ex.first and ex.last and ex.date):
            result.warnings.append(
                f"Sidor {[p+1 for p in group_pages]}: "
                f"namn={ex.full_name!r} datum={ex.date!r} — använder fallback-namn."
            )

        # Sidnummer för fallback-namn = första sidan i gruppen i originalet
        first_page_no = group_pages[0] + 1
        stem = build_filename(ex.first, ex.last, ex.date, first_page_no)
        out_path = unique_path(output_dir, stem, ".pdf")

        writer = PdfWriter()
        for p in group_pages:
            writer.add_page(reader.pages[p])
        with open(out_path, "wb") as f:
            writer.write(f)

        result.groups.append(GroupResult(
            pages_zero=group_pages,
            text=text,
            out_path=out_path,
            first=ex.first,
            last=ex.last,
            date=ex.date,
            name_rule=ex.debug.get("name_rule"),
            date_rule=ex.debug.get("date_rule"),
            fallback_used=not (ex.first and ex.last and ex.date),
        ))

    return result
