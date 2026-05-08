"""CLI-entry: `python -m lonespec_splitter <input.pdf> <outdir> [--ocr]`."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .log import write_log
from .splitter import split_pdf

EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_ENCRYPTED = 2
EXIT_INVALID_INPUT = 3
EXIT_OUTDIR_NOT_WRITABLE = 4


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lonespec-splitter",
        description="Splittar en samlad lönespec-PDF till en fil per person.",
    )
    p.add_argument("input_pdf", type=Path, help="Sökväg till samlad PDF.")
    p.add_argument("output_dir", type=Path, help="Mapp där utdatafilerna skrivs.")
    p.add_argument(
        "--ocr",
        action="store_true",
        help="Använd OCR (Tesseract, swe) för sidor utan extraherbar text.",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Mindre output på stdout.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.input_pdf.is_file():
        print(f"FEL: Hittar inte indata-PDF: {args.input_pdf}", file=sys.stderr)
        return EXIT_INVALID_INPUT

    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"FEL: Kan inte skapa utdatamapp ({e})", file=sys.stderr)
        return EXIT_OUTDIR_NOT_WRITABLE

    try:
        result = split_pdf(args.input_pdf, args.output_dir, use_ocr=args.ocr)
    except PermissionError as e:
        print(f"FEL: {e}", file=sys.stderr)
        return EXIT_ENCRYPTED
    except Exception as e:
        print(f"FEL: {e}", file=sys.stderr)
        logging.exception("Ohanterat undantag")
        return EXIT_GENERIC

    log_path = write_log(result)

    n = len(result.groups)
    n_warn = len(result.warnings)
    n_fb = sum(1 for g in result.groups if g.fallback_used)
    if not args.quiet:
        print(f"Klart: {n} fil(er) i {result.output_dir}")
        print(f"  Varav fallback-namn: {n_fb}")
        print(f"  Varningar: {n_warn}")
        print(f"  Logg: {log_path}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
