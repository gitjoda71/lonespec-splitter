"""End-to-end på de syntetiska fixture-PDF:erna."""
from pathlib import Path

import pytest

from lonespec_splitter.splitter import split_pdf

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module", autouse=True)
def ensure_fixtures():
    """Generera fixtures om de inte finns."""
    visma = FIXTURES / "fixture_visma_3personer.pdf"
    if not visma.is_file():
        from tests.fixtures.generate_fixtures import main as gen
        gen()


def test_visma_3_files(tmp_path: Path):
    result = split_pdf(FIXTURES / "fixture_visma_3personer.pdf", tmp_path)
    names = sorted(p.out_path.name for p in result.groups)
    assert names == [
        "Anna Andersson 2026-04-25.pdf",
        "Björn Bergström 2026-04-25.pdf",
        "Cecilia Östlund 2026-04-25.pdf",
    ]
    # Inga fallbacks
    assert all(not g.fallback_used for g in result.groups)


def test_hogia_2_files_2_pages_each(tmp_path: Path):
    result = split_pdf(FIXTURES / "fixture_hogia_2personer_2sidor.pdf", tmp_path)
    names = sorted(p.out_path.name for p in result.groups)
    assert names == [
        "Daniel Dahlqvist 2026-04-25.pdf",
        "Elin Ekström 2026-04-25.pdf",
    ]
    # Varje grupp ska ha 2 sidor
    for g in result.groups:
        assert len(g.pages_zero) == 2


def test_okant_format(tmp_path: Path):
    result = split_pdf(FIXTURES / "fixture_okant_format.pdf", tmp_path)
    assert len(result.groups) == 1
    g = result.groups[0]
    assert g.first == "Filip"
    assert g.last == "Forsberg"
    assert g.date == "2026-04-25"


def test_log_file_written(tmp_path: Path):
    from lonespec_splitter.log import write_log
    result = split_pdf(FIXTURES / "fixture_visma_3personer.pdf", tmp_path)
    log_path = write_log(result)
    assert log_path.is_file()
    text = log_path.read_text(encoding="utf-8")
    assert "Antal grupper: 3" in text
    assert "Anna Andersson" in text
