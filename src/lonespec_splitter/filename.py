"""Filnamnssanering och dubbletthantering.

Domänregler:
- Behåll svenska tecken (å/ä/ö och deras versaler).
- Ersätt OS-otillåtna tecken med understreck.
- Maxlängd 120 tecken inkl. extension.
- Vid kollision i målmappen: lägg till suffix `_1`, `_2`, ...
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# Tecken som inte är tillåtna i Windows-filnamn (även macOS-strikt).
_FORBIDDEN = re.compile(r'[\\/:*?"<>|\r\n\t]')
# Kontrolltecken
_CONTROL = re.compile(r"[\x00-\x1f]")
MAX_LEN = 120


def sanitize(name: str, replacement: str = "_") -> str:
    """Sanera ett filnamn (utan extension)."""
    if not name:
        return "OKAND"
    # NFC så att åäö är en kodpunkt, inte två
    name = unicodedata.normalize("NFC", name)
    name = _FORBIDDEN.sub(replacement, name)
    name = _CONTROL.sub("", name)
    # Komprimera multipla mellanslag/understreck
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"_{2,}", "_", name)
    # Ta bort ledande/avslutande punkter (Windows hatar dem)
    name = name.strip(". ")
    return name or "OKAND"


def build_filename(
    first: str | None,
    last: str | None,
    date: str | None,
    page_no: int,
) -> str:
    """Bygg ett filnamn (utan extension) enligt v0.1-regel.

    Lyckad extraktion → "Förnamn Efternamn YYYY-MM-DD"
    Misslyckad → "OKAND_sidaN"
    """
    name_parts = " ".join(p for p in (first, last) if p)
    if name_parts and date:
        base = f"{name_parts} {date}"
    elif date:
        base = f"OKAND_NAMN {date}"
    elif name_parts:
        base = f"{name_parts} OKANT_DATUM"
    else:
        base = f"OKAND_sida{page_no}"
    base = sanitize(base)
    if len(base) > MAX_LEN:
        base = base[:MAX_LEN].rstrip()
    return base


def unique_path(target_dir: Path, stem: str, ext: str = ".pdf") -> Path:
    """Returnera en sökväg som inte krockar i `target_dir`.

    Försöker `stem.ext`, sen `stem_1.ext`, `stem_2.ext`, ...
    """
    target_dir = Path(target_dir)
    candidate = target_dir / f"{stem}{ext}"
    if not candidate.exists():
        return candidate
    i = 1
    while True:
        candidate = target_dir / f"{stem}_{i}{ext}"
        if not candidate.exists():
            return candidate
        i += 1
