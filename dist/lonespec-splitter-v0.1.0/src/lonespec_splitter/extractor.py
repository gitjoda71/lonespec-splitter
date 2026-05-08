"""PDF text extraction via pdfplumber, med graceful degradation."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_per_page_text(pdf_path: Path) -> list[str]:
    """Returnera text för varje sida (index 0 = sida 1)."""
    import pdfplumber

    pages_text: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            try:
                text = page.extract_text() or ""
            except Exception as e:  # pragma: no cover
                logger.warning("extract_text misslyckades: %s", e)
                text = ""
            pages_text.append(text)
    return pages_text
