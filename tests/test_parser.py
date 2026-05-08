"""Unit-tester för parser (namn/datum)."""
import pytest

from lonespec_splitter.parser import (
    extract,
    extract_page_of_n,
    parse_date,
    parse_name,
)


class TestParseDate:
    def test_iso_with_keyword(self):
        d, rule = parse_date("Utbetalningsdatum: 2026-04-25")
        assert d == "2026-04-25"
        assert "keyword" in rule

    def test_lonedatum(self):
        d, _ = parse_date("Lönedatum: 2026-03-31")
        assert d == "2026-03-31"

    def test_slash_format(self):
        d, _ = parse_date("Utbetalningsdatum: 25/4/2026")
        assert d == "2026-04-25"

    def test_dot_format(self):
        d, _ = parse_date("Utbetalning 25.04.2026")
        assert d == "2026-04-25"

    def test_swedish_text_date(self):
        d, _ = parse_date("Utbetalas 25 april 2026")
        assert d == "2026-04-25"

    def test_short_swedish_month(self):
        d, _ = parse_date("Datum: 5 jan 2025")
        assert d == "2025-01-05"

    def test_two_digit_year_gt_80_is_1900s(self):
        d, _ = parse_date("Datum: 1/1/85")
        assert d == "1985-01-01"

    def test_two_digit_year_lt_80_is_2000s(self):
        d, _ = parse_date("Datum: 1/1/26")
        assert d == "2026-01-01"

    def test_no_date(self):
        d, rule = parse_date("Hej hej")
        assert d is None
        assert rule is None

    def test_first_iso_fallback(self):
        d, rule = parse_date("Anställd Anna 2026-04-25 betala")
        assert d == "2026-04-25"
        assert rule == "first-iso"


class TestParseName:
    def test_keyword_inline(self):
        first, last, _ = parse_name("Anställd: Anna Andersson")
        assert first == "Anna"
        assert last == "Andersson"

    def test_keyword_nextline(self):
        first, last, _ = parse_name("Mottagare:\nBjörn Bergström")
        assert first == "Björn"
        assert last == "Bergström"

    def test_above_pnr(self):
        text = "Cecilia Östlund\n19920811-0000 Period: 2026-04"
        first, last, _ = parse_name(text)
        assert first == "Cecilia"
        assert last == "Östlund"

    def test_inline_with_keyword_after(self):
        # Visma-mönstret: namn på samma rad som keyword
        text = "Anna Andersson Utbetalningsdatum: 2026-04-25\n19850517-0000 Period"
        first, last, _ = parse_name(text)
        assert first == "Anna"
        assert last == "Andersson"

    def test_three_part_name(self):
        first, last, _ = parse_name("Anställd: Anna Maria Andersson")
        assert first == "Anna Maria"
        assert last == "Andersson"

    def test_rejects_heading(self):
        first, last, _ = parse_name("VISMA Lönespecifikation\nFöretaget AB")
        assert first is None
        assert last is None

    def test_rejects_single_word(self):
        first, last, _ = parse_name("Anställd: Anna")
        assert first is None
        assert last is None

    # --- Kontek-formatet: "Mottagare\nDanielsson, Joel" ---
    def test_kontek_keyword_no_colon_nextline_komma(self):
        text = "Mottagare\nDanielsson, Joel"
        first, last, rule = parse_name(text)
        assert first == "Joel"
        assert last == "Danielsson"
        assert "komma" in rule

    def test_kontek_with_colon_komma(self):
        text = "Mottagare: Andersson, Anna Maria"
        first, last, _ = parse_name(text)
        assert first == "Anna Maria"
        assert last == "Andersson"

    def test_kontek_skips_blank_line(self):
        text = "Mottagare\n\nÖstlund, Cecilia"
        first, last, _ = parse_name(text)
        assert first == "Cecilia"
        assert last == "Östlund"

    def test_komma_first_line_fallback(self):
        # Ingen keyword men "Efternamn, Förnamn" på första raden
        text = "Bergström, Björn\nNågon annan text"
        first, last, _ = parse_name(text)
        assert first == "Björn"
        assert last == "Bergström"

    def test_kontek_rejects_company(self):
        # Visa att vi inte plockar "Kontek, AB"
        text = "Mottagare\nKontek, AB"
        first, last, _ = parse_name(text)
        assert first is None
        assert last is None

    def test_kontek_double_lastname(self):
        # Dubbla efternamn — vanligt i svenska lönesystem
        text = "Mottagare\nDanielsson Svensson, Joel"
        first, last, _ = parse_name(text)
        assert first == "Joel"
        assert last == "Danielsson Svensson"

    def test_kontek_double_lastname_three_word_first(self):
        text = "Mottagare\nÖstlund Bergström, Anna Maria Britt"
        first, last, _ = parse_name(text)
        assert first == "Anna Maria Britt"
        assert last == "Östlund Bergström"

    def test_kontek_double_lastname_inline_keyword(self):
        text = "Mottagare: Larsson Holm, Erik"
        first, last, _ = parse_name(text)
        assert first == "Erik"
        assert last == "Larsson Holm"


class TestExtractPageOfN:
    def test_sida_x_av_y(self):
        assert extract_page_of_n("Sida 1 av 2") == (1, 2)

    def test_sida_x_paren(self):
        assert extract_page_of_n("Sida 2 (3)") == (2, 3)

    def test_x_paren(self):
        assert extract_page_of_n("foo bar\n2 (3)") == (2, 3)

    def test_no_match(self):
        assert extract_page_of_n("Bara text") is None


class TestExtract:
    def test_full_extraction(self):
        text = (
            "VISMA Lönespecifikation\n"
            "Anna Andersson Utbetalningsdatum: 2026-04-25\n"
            "19850517-0000 Period: 2026-04-01\n"
        )
        ex = extract(text)
        assert ex.first == "Anna"
        assert ex.last == "Andersson"
        assert ex.date == "2026-04-25"
        assert ex.full_name == "Anna Andersson"
