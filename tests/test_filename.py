"""Unit-tester för filnamnssanering och dubbletthantering."""
from pathlib import Path

import pytest

from lonespec_splitter.filename import build_filename, sanitize, unique_path


class TestSanitize:
    def test_keeps_swedish_chars(self):
        assert sanitize("Björn Östlund") == "Björn Östlund"

    def test_strips_forbidden(self):
        assert sanitize('Anna/Anders\\son') == "Anna_Anders_son"

    def test_collapses_whitespace(self):
        assert sanitize("Anna   Andersson") == "Anna Andersson"

    def test_strips_leading_dots(self):
        assert sanitize("..Anna") == "Anna"

    def test_empty_returns_okand(self):
        assert sanitize("") == "OKAND"
        assert sanitize("   ") == "OKAND"

    def test_control_chars_removed(self):
        assert sanitize("Anna\x00\x01") == "Anna"


class TestBuildFilename:
    def test_full_info(self):
        assert build_filename("Anna", "Andersson", "2026-04-25", 3) == "Anna Andersson 2026-04-25"

    def test_no_name(self):
        assert build_filename(None, None, "2026-04-25", 3) == "OKAND_NAMN 2026-04-25"

    def test_no_date(self):
        assert build_filename("Anna", "Andersson", None, 3) == "Anna Andersson OKANT_DATUM"

    def test_nothing(self):
        assert build_filename(None, None, None, 7) == "OKAND_sida7"

    def test_swedish_chars_preserved(self):
        assert build_filename("Cecilia", "Östlund", "2026-04-25", 1) == "Cecilia Östlund 2026-04-25"


class TestUniquePath:
    def test_first_use(self, tmp_path: Path):
        p = unique_path(tmp_path, "Anna Andersson 2026-04-25")
        assert p.name == "Anna Andersson 2026-04-25.pdf"

    def test_collision_adds_suffix(self, tmp_path: Path):
        (tmp_path / "X.pdf").write_bytes(b"")
        p = unique_path(tmp_path, "X")
        assert p.name == "X_1.pdf"

    def test_multiple_collisions(self, tmp_path: Path):
        (tmp_path / "X.pdf").write_bytes(b"")
        (tmp_path / "X_1.pdf").write_bytes(b"")
        (tmp_path / "X_2.pdf").write_bytes(b"")
        p = unique_path(tmp_path, "X")
        assert p.name == "X_3.pdf"
