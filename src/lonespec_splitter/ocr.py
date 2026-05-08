"""OCR-fallback (best effort i v0.1).

Kräver:
- Tesseract installerat på systemet (med svenska språkdatat: `tesseract-ocr-swe`).
- Python-paketen `pytesseract` och `pdf2image` (lyfter dem on-demand).

Saknas något: returnera tom sträng + logga.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """Är Tesseract i PATH?"""
    return shutil.which("tesseract") is not None


def ocr_page(pdf_path: Path, page_index_zero: int, lang: str = "swe") -> str:
    """OCR:a en specifik sida och returnera text. Tom sträng vid fel."""
    if not is_available():
        logger.info("Tesseract saknas — hoppar OCR")
        return ""
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError as e:
        logger.info("OCR-beroenden saknas (%s) — hoppar OCR", e)
        return ""

    try:
        images = convert_from_path(
            str(pdf_path),
            first_page=page_index_zero + 1,
            last_page=page_index_zero + 1,
            dpi=200,
        )
        if not images:
            return ""
        return pytesseract.image_to_string(images[0], lang=lang) or ""
    except Exception as e:  # pragma: no cover
        logger.warning("OCR-fel på sida %d: %s", page_index_zero + 1, e)
        return ""
