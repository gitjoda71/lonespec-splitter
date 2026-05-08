"""Parsning av lönespec-text: namn + datum.

Heuristikerna är ordnade i prioritet — första som ger ett rimligt resultat vinner.
Stöd v0.1: Visma-, Hogia-liknande och generiska layouter.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# --- Regex-byggstenar ---
SVENSKT_NAMN_TECKEN = r"A-Za-zÅÄÖåäöÉéÜüÆæØøÁáÍíÚúÝý"
# En namn-del måste börja med stor bokstav följt av minst en gemen
# (avvisar rubriker som "VISMA" eller all-caps-keywords).
NAMN_DEL = (
    rf"[A-ZÅÄÖÉÜÆØÁÍÚÝ][a-zåäöéüæøáíúý][{SVENSKT_NAMN_TECKEN}'\-]*"
)
# Förnamn + (mellannamn) + Efternamn — minst två delar
NAMN_FULL = rf"{NAMN_DEL}(?:\s+{NAMN_DEL}){{1,3}}"

# Ord vi aldrig accepterar som del av ett extraherat namn (rubriker/keywords).
NAMN_BLOCKLISTA = {
    "lönespecifikation", "lonespecifikation", "lönespec", "lonespec",
    "löneavi", "loneavi", "lönedatum", "lonedatum",
    "utbetalningsdatum", "utbetalning", "betalningsdag",
    "anställd", "anstalld", "namn", "mottagare", "betalningsmottagare",
    "personnummer", "period", "avdelning", "datum", "till",
    "visma", "hogia", "fortnox",
    "sida", "av", "sammanställning", "sammanstallning",
    "bruttolön", "bruttolon", "skatt", "netto", "nettolön", "nettolon",
    "att", "utbetala", "detaljerad", "löneberäkning", "loneberakning",
}


def _name_has_blocked_word(full_name: str) -> bool:
    """True om något ord i namnet finns i blocklistan."""
    return any(w.lower() in NAMN_BLOCKLISTA for w in full_name.split())


def _trim_at_blocked(full_name: str) -> str:
    """Trunkera namnet vid första ord som är i blocklistan.

    'Daniel Dahlqvist Lönedatum' → 'Daniel Dahlqvist'
    """
    out: list[str] = []
    for w in full_name.split():
        if w.lower() in NAMN_BLOCKLISTA:
            break
        out.append(w)
    return " ".join(out)

# Personnummer: 6 eller 8 inledande siffror, valfri separator, 4 slut
PERSONNUMMER = re.compile(r"\b(?:19|20)?\d{6}[-+]?\d{4}\b")

SVENSKA_MANADER = {
    "januari": 1, "jan": 1,
    "februari": 2, "feb": 2,
    "mars": 3, "mar": 3,
    "april": 4, "apr": 4,
    "maj": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "augusti": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# Datum-mönster
DATUM_ISO = re.compile(r"\b(?P<y>(?:19|20)\d{2})-(?P<m>0[1-9]|1[0-2])-(?P<d>0[1-9]|[12]\d|3[01])\b")
DATUM_SLASH = re.compile(r"\b(?P<d>0?[1-9]|[12]\d|3[01])[/.](?P<m>0?[1-9]|1[0-2])[/.](?P<y>(?:19|20)?\d{2})\b")
_man_alt = "|".join(SVENSKA_MANADER.keys())
DATUM_TEXT = re.compile(rf"\b(?P<d>0?[1-9]|[12]\d|3[01])\s+(?P<m>{_man_alt})\s+(?P<y>(?:19|20)\d{{2}})\b", re.IGNORECASE)

# Datum-keywords (i prioritetsordning)
DATUM_KEYWORDS = [
    "utbetalningsdatum",
    "utbetalning",
    "lönedatum",
    "lonedatum",
    "avsedd för utbetalning",
    "avsedd for utbetalning",
    "betalningsdag",
    "datum",
]

# Namn-keywords
NAMN_KEYWORDS = [
    "anställd", "anstalld",
    "namn",
    "mottagare",
    "betalningsmottagare",
    "till",
]


@dataclass
class Extracted:
    first: str | None
    last: str | None
    date: str | None  # alltid YYYY-MM-DD eller None
    debug: dict[str, str]

    @property
    def full_name(self) -> str | None:
        if self.first and self.last:
            return f"{self.first} {self.last}"
        return self.first or self.last


def normalize_text(s: str) -> str:
    """Normalisera till NFC + ersätt CRLF med LF."""
    return unicodedata.normalize("NFC", s.replace("\r\n", "\n").replace("\r", "\n"))


def _two_digit_year_to_full(y: str) -> str:
    """Översätt tvåsiffrigt år till fyrsiffrigt med rimlig pivot."""
    if len(y) == 4:
        return y
    yi = int(y)
    # 00-79 → 2000-tal, 80-99 → 1900-tal
    return f"20{yi:02d}" if yi < 80 else f"19{yi:02d}"


def parse_date(text: str) -> tuple[str | None, str | None]:
    """Returnera (YYYY-MM-DD, vilken-regel-matchade) eller (None, None).

    Letar i prioritetsordning baserat på keywords. Faller tillbaka till
    "första rimliga datum hittills" om inget keyword-träff.
    """
    text_lc = text.lower()

    # 1) Försök hitta datum nära ett keyword (samma rad eller nästa).
    for kw in DATUM_KEYWORDS:
        for kw_match in re.finditer(re.escape(kw), text_lc):
            # Slice fönster på 80 tecken efter keyword
            window = text[kw_match.start(): kw_match.start() + 200]
            iso = DATUM_ISO.search(window)
            if iso:
                return f"{iso['y']}-{iso['m']}-{iso['d']}", f"keyword:{kw}+iso"
            sl = DATUM_SLASH.search(window)
            if sl:
                y = _two_digit_year_to_full(sl["y"])
                return f"{y}-{int(sl['m']):02d}-{int(sl['d']):02d}", f"keyword:{kw}+slash"
            tx = DATUM_TEXT.search(window)
            if tx:
                m = SVENSKA_MANADER[tx["m"].lower()]
                return f"{tx['y']}-{m:02d}-{int(tx['d']):02d}", f"keyword:{kw}+text"

    # 2) Fallback: första ISO-datum i hela texten.
    iso = DATUM_ISO.search(text)
    if iso:
        return f"{iso['y']}-{iso['m']}-{iso['d']}", "first-iso"

    # 3) Första slash/text-datum i hela texten.
    sl = DATUM_SLASH.search(text)
    if sl:
        y = _two_digit_year_to_full(sl["y"])
        return f"{y}-{int(sl['m']):02d}-{int(sl['d']):02d}", "first-slash"
    tx = DATUM_TEXT.search(text)
    if tx:
        m = SVENSKA_MANADER[tx["m"].lower()]
        return f"{tx['y']}-{m:02d}-{int(tx['d']):02d}", "first-text"

    return None, None


def _split_first_last(full: str) -> tuple[str, str]:
    """Dela 'Förnamn Mellan Efternamn' → ('Förnamn Mellan', 'Efternamn').

    v0.1: enkla tumregeln "sista ordet = efternamn", resten = förnamn(en).
    """
    parts = full.split()
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def _accept_name(full: str) -> tuple[str, str] | None:
    """Trimma vid blockerade ord, dela first/last. None om resultatet är degenererat."""
    full = _trim_at_blocked(full).strip()
    if not full:
        return None
    if _name_has_blocked_word(full):
        return None
    parts = full.split()
    if len(parts) < 2:
        return None
    first, last = _split_first_last(full)
    if not last:
        return None
    return first, last


def parse_name(text: str) -> tuple[str | None, str | None, str | None]:
    """Returnera (first, last, regel-namn) eller (None, None, None)."""
    lines = [ln.strip() for ln in text.split("\n")]

    name_re_full = re.compile(rf"^({NAMN_FULL})\s*$")
    name_re_inline = re.compile(rf"({NAMN_FULL})")

    # Strategi 1: rad efter ett namn-keyword (ex. "Anställd: Anna Andersson")
    for i, line in enumerate(lines):
        low = line.lower()
        for kw in NAMN_KEYWORDS:
            if low.startswith(kw + ":") or low.startswith(kw + " "):
                rest = line.split(":", 1)[-1].strip() if ":" in line else line[len(kw):].strip()
                m = name_re_inline.search(rest)
                if m:
                    fl = _accept_name(m.group(1))
                    if fl:
                        return fl[0], fl[1], f"keyword-inline:{kw}"
                if i + 1 < len(lines):
                    nm = name_re_full.match(lines[i + 1])
                    if nm:
                        fl = _accept_name(nm.group(1))
                        if fl:
                            return fl[0], fl[1], f"keyword-nextline:{kw}"

    # Strategi 2: rad direkt OVANFÖR ett personnummer
    for i, line in enumerate(lines):
        if PERSONNUMMER.search(line):
            same = re.match(rf"^({NAMN_FULL})\s+(?:{PERSONNUMMER.pattern})", line)
            if same:
                fl = _accept_name(same.group(1))
                if fl:
                    return fl[0], fl[1], "above-pnr-same-line"
            # Gå uppåt max 3 rader för att hitta en namn-liknande sekvens
            # (inline-match — raden kan börja med namnet och fortsätta med keywords).
            for j in range(i - 1, max(-1, i - 4), -1):
                nm_full = name_re_full.match(lines[j])
                if nm_full:
                    fl = _accept_name(nm_full.group(1))
                    if fl:
                        return fl[0], fl[1], "above-pnr-prev-line"
                # Inline: ta första matchningen och försök trimma vid keyword
                nm_inline = name_re_inline.search(lines[j])
                if nm_inline:
                    fl = _accept_name(nm_inline.group(1))
                    if fl:
                        return fl[0], fl[1], "above-pnr-prev-line-inline"

    # Strategi 3: första raden som ser ut som ett komplett namn
    for line in lines[:20]:
        nm = name_re_full.match(line)
        if nm:
            fl = _accept_name(nm.group(1))
            if fl:
                return fl[0], fl[1], "first-name-like-line"

    return None, None, None


def extract(text: str) -> Extracted:
    """Top-level: tar text från en spec (1+ sidor) och returnerar Extracted."""
    text = normalize_text(text)
    first, last, name_rule = parse_name(text)
    date, date_rule = parse_date(text)
    return Extracted(
        first=first,
        last=last,
        date=date,
        debug={
            "name_rule": name_rule or "<none>",
            "date_rule": date_rule or "<none>",
        },
    )


def extract_personnummer_pages(per_page_text: list[str]) -> list[int]:
    """Returnera index för sidor som innehåller ett personnummer."""
    return [i for i, t in enumerate(per_page_text) if PERSONNUMMER.search(t)]


def extract_page_of_n(text: str) -> tuple[int, int] | None:
    """Hitta 'Sida X av Y' eller 'Sida X (Y)' eller 'X (Y)' nederst på sidan."""
    m = re.search(r"\bsida\s+(\d+)\s+av\s+(\d+)\b", text, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\bsida\s+(\d+)\s*\(\s*(\d+)\s*\)", text, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\b(\d+)\s*\(\s*(\d+)\s*\)\s*$", text.strip(), re.MULTILINE)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if 1 <= a <= b <= 50:
            return a, b
    return None
