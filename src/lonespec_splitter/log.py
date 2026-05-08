"""Skriv ett människoläsligt _split_log.txt till utdatamappen."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from .splitter import SplitResult


def write_log(result: SplitResult) -> Path:
    log_path = result.output_dir / "_split_log.txt"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append(f"Lonespec-splitter — körlogg")
    lines.append(f"Tidpunkt:   {now}")
    lines.append(f"Indata:     {result.input_path}")
    lines.append(f"Utdatamapp: {result.output_dir}")
    lines.append(f"Antal grupper: {len(result.groups)}")
    lines.append("")
    lines.append("=== Filer ===")
    for i, g in enumerate(result.groups, 1):
        sid_str = ",".join(str(p + 1) for p in g.pages_zero)
        lines.append(
            f"{i:3d}. sidor [{sid_str}]  →  {g.out_path.name}"
            f"  (regel: namn={g.name_rule}, datum={g.date_rule}"
            f"{', FALLBACK' if g.fallback_used else ''})"
        )
    if result.warnings:
        lines.append("")
        lines.append("=== Varningar ===")
        for w in result.warnings:
            lines.append(f"- {w}")
    if result.errors:
        lines.append("")
        lines.append("=== Fel ===")
        for e in result.errors:
            lines.append(f"- {e}")
    # utf-8-sig så Notepad och äldre Windows-verktyg känner igen UTF-8
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return log_path
