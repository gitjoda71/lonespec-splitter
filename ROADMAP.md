# ROADMAP — PDF-Splitter för Lönespecar (Acrobat-plugin)

> Projektnamn (arbetsnamn): **lonespec-splitter**
> Mål: Split + namnge varje persons lönespec i en samlad flersidig PDF, körbart från Adobe Acrobat Pro DC.
> Status: planeringsfas, byggs iterativt mot v0.1.0 (live).

---

## 1. Teknikval

### Utvärderade alternativ

| Alternativ | För | Emot | Bedömning |
|---|---|---|---|
| **A. Acrobat JavaScript (folder-level + Action Wizard)** | Inga externa beroenden, körs i Acrobat, lätt att distribuera (kopiera in `.js`-fil). | Acrobats inbyggda JS-motor saknar moderna regex-features, ingen fil-IO utanför privilegierat läge utan godkännande, klumpig text-extraktion (`getPageNthWord`/`getPageNthWordQuads`), ingen OCR. | Räcker som UI-trigger, **inte** som hela motorn. |
| **B. UXP-plugin för Acrobat** | Modern stack (HTML/JS/CSS), bättre DX. | UXP för Acrobat är fortfarande relativt ung, kräver Adobe Developer-konto för signering vid distribution, mognaden för PDF-manipulation är begränsad. Overkill för v0.1.0. | Förkastas för v0.1. |
| **C. Acrobat SDK (C/C++)** | Maximal kontroll. | Tung onboarding, Visual Studio-toolchain, NDA, signerade plugins krävs (`.api`-filer). Veckor till första bygge. | Förkastas. |
| **D. Hybrid: Acrobat JS-trigger + Python-backend** | Python = mogen ekosystem för PDF (`pypdf`, `pdfplumber`) + OCR (`pytesseract`). Acrobat JS levererar bara filväg + folder-picker. Snabbaste vägen till robust v0.1.0. | Kräver att Python är installerat på användarens dator (ej show-stopper — användaren har redan Python 3.12). Två moving parts. | **VALD.** |

### Beslut: **Alternativ D — Hybrid**

**Motivering:**
- Användaren har redan Python 3.12.10 installerat (verifierat).
- `pypdf` ger oss splittning, `pdfplumber` ger oss text-extraktion med svensk åäö-support, `pytesseract` ger OCR-fallback.
- Acrobat-sidan blir så liten att hela trigger-skriptet får plats i en `.js`-fil som droppas i `JavaScripts/`-mappen + ett Action Wizard-makro (`.sequ`) — inga signerings-headache.
- Standalone CLI-läge gör att backend kan testas och köras utan Acrobat (viktigt för CI och pytest).

### Slutarkitektur — komponenter

```
┌─────────────────────────────────┐
│ Adobe Acrobat Pro DC            │
│  ┌───────────────────────────┐  │
│  │ Action: "Splitta lönespec" │  │ ← Action Wizard .sequ
│  │  → kallar folder-level JS  │  │
│  └────────────┬──────────────┘  │
│               │                  │
│  ┌────────────▼──────────────┐  │
│  │ lonespec_splitter.js       │  │ ← Folder-level script
│  │  - får aktivt dokument     │  │   (i privileged JS-mappen)
│  │  - visar folder-picker     │  │
│  │  - sparar PDF tillfälligt  │  │
│  │  - app.launchURL/exec ─────┼──┼──► Python-backend
│  └───────────────────────────┘  │
└─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ Python-backend (CLI)             │
│  src/lonespec_splitter/          │
│   ├── __main__.py     (CLI)      │
│   ├── splitter.py     (pypdf)    │
│   ├── extractor.py    (pdfplumber)│
│   ├── ocr.py          (pytesseract, valfri) │
│   ├── parser.py       (regex för namn/datum) │
│   ├── filename.py     (sanering) │
│   └── log.py                     │
└─────────────────────────────────┘
                │
                ▼
        Utdatamapp/
         ├── Anna Andersson 2026-04-25.pdf
         ├── Bo Bengtsson 2026-04-25.pdf
         ├── ...
         └── _split_log.txt
```

---

## 2. Arkitektur i detalj

### Dataflöde
1. Användaren öppnar samlad lönespec-PDF i Acrobat Pro DC.
2. Klickar Action: "Splitta lönespec" (eller högerklick-meny).
3. JS-skriptet visar mapp-väljare (via `app.browseForDoc` / fallback `app.response`).
4. JS sparar aktivt dokument till temp-path och anropar Python-CLI:
   `python -m lonespec_splitter "<input.pdf>" "<outdir>"`
5. Python:
   - Öppnar PDF, går igenom sidorna.
   - Bestämmer **sidgrupperingar** (en lönespec = 1+ sidor) via heuristik:
     - Återkommande personnummer på första sidan av varje spec.
     - "Sida 1 av N" eller "1 (N)" som ankarpunkt.
     - Layout-anchor: rad innehållande "Lönespecifikation"/"Löneavi" + datum.
     - Default-fallback: 1 sida = 1 spec (säkert minimum för v0.1).
   - För varje grupp: extrahera namn + datum, bygg filnamn, skriv ut PDF.
   - Logga till `_split_log.txt`.
6. Python returnerar exit-kod; JS visar `app.alert` med summering.

### Sidgrupperings-strategi (v0.1)
Implementeras i tre lager (försök i ordning, första som lyckas vinner):
1. **Personnummer-cluster:** hitta alla sidor där rad matchar `\d{6,8}[-+]?\d{4}`. Varje sådan sida = början på ny spec, sidor mellan = fortsättning.
2. **Sidnumrering:** "Sida 1 av N" / "1 (N)" → grupper byggs av hela block.
3. **En-sida-per-spec:** fallback om ingen anchor hittas.

### Namn-extraktion
- Sök efter följande mönster (i prioritetsordning):
  - Rad efter "Anställd:" / "Namn:" / "Mottagare:"
  - Rad ovanför personnummer (vanligt i Visma/Hogia)
  - Översta capitalised "Förnamn Efternamn"-raden på sidan
- Behåll svenska tecken (å/ä/ö/Å/Ä/Ö, é, ü).

### Datum-extraktion
- Leta i prioritetsordning efter:
  - "Utbetalningsdatum: YYYY-MM-DD"
  - "Lönedatum: YYYY-MM-DD"
  - "Avsedd för utbetalning: YYYY-MM-DD"
  - "Datum: YYYY-MM-DD" (sista utvägen)
- Stöd även `DD/MM/YYYY`, `DD.MM.YYYY` och `DD MMM YYYY` (svenska månadsnamn) — normaliseras alltid till `YYYY-MM-DD`.

### Filnamnssanering
- Tillåtna tecken: bokstäver (inkl. åäö), siffror, mellanslag, bindestreck, understreck, punkt.
- Otillåtna ersätts med `_`.
- Längdtak: 120 tecken.
- Dubbletter: `_1`, `_2`, …

---

## 3. Milstolpar

### M1 — Python-backend MVP (kärnsplit)
**Acceptanskriterier:**
- `python -m lonespec_splitter input.pdf outdir/` kör utan fel på en textbaserad PDF.
- En sida per spec antas (fallback-läge).
- Genererar filnamn `Förnamn Efternamn YYYY-MM-DD.pdf` när text hittas, annars `OKAND_sidaN.pdf`.
- Skriver `_split_log.txt`.
- pytest-test passerar för minst en fixture-PDF.

### M2 — Test-fixtures
**Acceptanskriterier:**
- 3 syntetiska test-PDF:er checkade in i `tests/fixtures/`:
  - `fixture_visma_3personer.pdf` (Visma-liknande, 1 sida/person)
  - `fixture_hogia_2personer_2sidor.pdf` (Hogia-liknande, 2 sidor/person)
  - `fixture_okant_format.pdf` (helt avvikande layout, edge-case)
- Genereringsskript `tests/fixtures/generate_fixtures.py` deterministiskt (samma indata → samma PDF-bytes).

### M3 — Smart sidgruppering + flera layouter
**Acceptanskriterier:**
- Personnummer-cluster + "Sida X av Y"-heuristik fungerar.
- `fixture_hogia_2personer_2sidor.pdf` → exakt 2 utfiler, korrekt namngivna.
- Regex för Visma + Hogia + generisk gröngöling.

### M4 — Acrobat-integration
**Acceptanskriterier:**
- `lonespec_splitter.js` (folder-level) installerad i `%APPDATA%\Adobe\Acrobat\DC\JavaScripts\`.
- Action Wizard `.sequ` som triggar skriptet.
- End-to-end manuell körning: öppna PDF i Acrobat, kör Action, få filer i vald mapp.
- Tydligt felmeddelande om Python saknas eller backend kraschar.

### M5 — OCR-fallback
**Acceptanskriterier:**
- Sidor utan extraherbar text körs genom Tesseract (`-l swe`).
- Graceful degradation: OCR är optional dependency, saknas Tesseract loggas det och faller tillbaka till `OKAND_sidaN`.
- Markeras som "best effort" i v0.1.

### M6 — Paketering & Release
**Acceptanskriterier:**
- `dist/lonespec-splitter-v0.1.0.zip` med:
  - Python-källkod
  - `lonespec_splitter.js`
  - `Splitta lönespec.sequ`
  - `INSTALL.md`
  - `requirements.txt`
- GitHub Actions workflow bygger ZIP vid tag `v*`.
- GitHub Release skapad, ZIP attachad.

---

## 4. Riskanalys

| Risk | Sannolikhet | Påverkan | Mitigering |
|---|---|---|---|
| Krypterade/lösenordsskyddade PDF:er | Låg–medel | Hög | `pypdf` upptäcker → backend exit med felkod 2, JS visar "Lås upp PDF:en först". |
| Scannade/bildbaserade sidor | Medel | Hög | OCR-fallback i M5. v0.1: skapar `OKAND_sidaN.pdf` om OCR saknas. |
| Varierande layout mellan lönesystem | Hög | Medel | Multi-mönster-regex + ordnad fallback. Layout-detektor (bestämmer "system" baserat på keywords på första sidan). |
| Flera sidor per person ej upptäckta | Medel | Hög | Personnummer-cluster + "Sida X av Y"-detektor. Vid osäkerhet: 1 sida = 1 spec (säkert default, värsta fall = oversplit). |
| Svenska tecken (å/ä/ö) i filnamn | Säker | Låg | UTF-8 + NFC-normalisering. Windows-filsystem hanterar dem. |
| Datumformat (svenska "25 april 2026", "2026-04-25", "25/4-26") | Hög | Medel | `dateutil` + handgjorda svenska månadsnamn. Misslyckas → använd dagens datum + `_OKANT_DATUM`. |
| Python saknas på användarens dator | Låg (verifierat installerat) | Hög | Installer-script kollar `python --version`. Annars länk till python.org. |
| Acrobat-säkerhetsrestriktioner blockerar `app.execMenuItem` / `Doc.extractPages` | Medel | Medel | Folder-level skript = privilegierat, kringgår de flesta restriktioner. Dokumenteras i INSTALL.md. |
| Filer öppnade i Acrobat = låsta för skrivning | Medel | Låg | Spara temp till annan mapp än indata; varna om utdata = samma mapp som öppen fil. |

---

## 5. Test- och deploymentplan

### Test
- **Unit (pytest):**
  - `test_parser.py` — namn/datum-regex på textsträngar.
  - `test_filename.py` — sanering, dubbletter, längdtak.
  - `test_splitter.py` — gruppering på syntetiska PDF:er.
- **Integration:**
  - End-to-end på alla 3 fixture-PDF:er, jämför mot förväntade filnamn.
- **Manuell:**
  - Verklig lönespec (användarens egen, körs inte i CI).

### CI
GitHub Actions:
- `ci.yml`: vid push/PR — kör pytest på Windows + Linux, Python 3.11/3.12.
- `release.yml`: vid tag `v*` — bygg ZIP, skapa Release.

### Deployment
- v0.1.0 → GitHub Release med ZIP. Användare laddar ner, kör `install.ps1` (Windows) som:
  1. Verifierar Python.
  2. `pip install -r requirements.txt`.
  3. Kopierar `lonespec_splitter.js` till `%APPDATA%\Adobe\Acrobat\DC\JavaScripts\`.
  4. Kopierar `.sequ` till Sequences-mappen.
- Manuell installation dokumenteras i INSTALL.md som fallback.

---

## 6. Definition of Done — v0.1.0

- [ ] ROADMAP, SPEC, README, CHANGELOG, LICENSE finns och är konsistenta.
- [ ] Python-backend kör som `python -m lonespec_splitter` på Windows.
- [ ] Minst 3 fixture-PDF:er + automatiserade tester (pytest grön).
- [ ] Acrobat JS-skript + Action installerbar via `install.ps1`.
- [ ] End-to-end: öppna fixture i Acrobat, kör Action, få korrekt namngivna utfiler.
- [ ] GitHub-repo publikt, GH Actions grön på senaste main.
- [ ] Release v0.1.0 publicerad med ZIP-artefakt.
- [ ] INSTALL.md läsbar för en icke-utvecklare.

---

## 7. Repo-val: publikt vs privat

**Beslut: PUBLIKT** (`github.com/gitjoda71/lonespec-splitter`).

**Motivering:** Innehåller ingen persondata (alla fixtures är syntetiska). MIT-licens. Återanvändbart för andra med samma problem. Synkar bäst med "snabbt live" — privata repos kräver login för Release-nedladdning, vilket gör INSTALL.md krångligare.

---

## 8. Decision log

- **2026-05-08:** Vald hybrid-arkitektur (Acrobat JS-trigger + Python-backend) framför ren UXP/Acrobat-JS-lösning. Python finns redan på dev-maskinen, ekosystemet för PDF-parsing är moget.
- **2026-05-08:** v0.1 antar **1 sida = 1 spec som säker fallback**. Smart gruppering är M3, inte blockerande för release.
- **2026-05-08:** OCR är optional i v0.1 (M5). Sidor utan text → `OKAND_sidaN.pdf` om Tesseract saknas.
- **2026-05-08:** Repo publikt, MIT-licens.
- **2026-05-08:** Använder `reportlab` för att generera fixture-PDF:er (välkänt, deterministiskt).
- **2026-05-08:** Installer-script Windows-only i v0.1 (manuell macOS-instruktion i INSTALL.md, automatiseras i v0.2).

---

## 9. v0.2.0 — Gmail-drafting

**Mål:** Efter split skapas Gmail-utkast automatiskt för varje lönespec.
- Mottagare: slå upp medarbetarens `@workspace.se`-email via Google Workspace Directory API.
- Ämne: `Lönespecifikation [utbetalningsdatum]`
- Body: enkel template (`Hej {namn}, Se bifogad lönespecifikation för period {periode} (utbetald {datum}).`)
- Åtgärd: lagra som DRAFT i Gmail (ej skicka).
- Användaren granskar utkastmappen i Gmail → skickar manuellt.

### Teknikval för v0.2

| Komponent | Val | Motivering |
|---|---|---|
| **Auth** | Service Account (JSON-nyckel) | Backend-process behöver inga interaktiva inloggningar. Skapas i Google Cloud Console per workspace. |
| **Directory API** | Google Workspace Directory API | Slår upp namn → email. Kräver att workspace-admin har aktiverat API och delegerat behörighet. |
| **Gmail API** | `google-auth-oauthlib` + `google-auth-httplib2` | Officiell SDK, mogen. Skapa DRAFT via `messages.create()` utan att skicka. |
| **Config** | YAML + environment var | `gmail_config.yaml` lagrar workspace-domän, service-account-nyckel-path. Denna checkas INTE in (`.gitignore`). |
| **Error handling** | Graceful degradation | Saknas Directory API-nyckel → skapa DRAFT med bara namn (fallback). Gmail API-fel → logg + gå vidare med nästa person. |

### Arkitektur v0.2

```
┌────────────────────────────────────────────────┐
│ Python-backend (CLI) — UTÖKAD              │
│  src/lonespec_splitter/                        │
│   ├── __main__.py         (CLI + argparse)     │
│   ├── splitter.py         (oförändrad)         │
│   ├── parser.py           (oförändrad)         │
│   ├── filename.py         (oförändrad)         │
│   ├── log.py              (oförändrad)         │
│   ├── extractor.py        (oförändrad)         │
│   │                                            │
│   ├── gmail_draft.py       [NYT]               │ ← Gmail-modul
│   │  ├── GmailDrafter(config_path)             │   - service account auth
│   │  ├── lookup_email(name) → email            │   - Directory API lookup
│   │  ├── create_draft(to, subject, body)       │   - Gmail draft create
│   │  └── render_template(name, datum, period) │   - template rendering
│   │                                            │
│   └── gmail_config.py      [NYT]               │ ← Config handling
│      ├── load_config(yaml_path)                │
│      └── validate_keys()                       │
└────────────────────────────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │ Google Workspace             │
    │  ├─ Directory API            │
    │  │  (namn → email lookup)     │
    │  └─ Gmail API                │
    │     (create draft)            │
    └──────────────────────────────┘
```

### Milstolpar v0.2

#### M7 — Gmail-modul (auth + API-wrappers)
**Acceptanskriterier:**
- `GmailDrafter`-klass med Service Account-auth.
- `lookup_email(name)` mot Directory API (mock-testbar).
- `create_draft(to, subject, body)` mot Gmail API.
- Unit-tester (mocked API:er).

#### M8 — Config + template
**Acceptanskriterier:**
- `gmail_config.yaml` template-fil med instruktioner.
- `GmailDrafter.render_template()` för ämneslinje + brödtext.
- Tester för mallar.

#### M9 — CLI-integrering
**Acceptanskriterier:**
- `lonespec_splitter --with-gmail --gmail-config ./gmail_config.yaml input.pdf outdir/`
- Efter split: för varje PDf-fil → slå upp email → skapa DRAFT.
- Logga draft-skapning i `_split_log.txt`.

#### M10 — Tester + docs
**Acceptanskriterier:**
- Integration-tester med mocked Gmail/Directory API:er.
- `GMAIL_SETUP.md` — instruktion för workspace-admin att delegera API-åtkomst.
- `CHANGELOG.md` updated.

#### M11 — Release v0.2.0
**Acceptanskriterier:**
- GitHub tag `v0.2.0`, ZIP-artefakt med ny kod.
- `requirements.txt` updated (Google SDK:er tillagda).

---

## Decision log (v0.2)

- **2026-05-08:** Vald Service Account för auth (ej OAuth2 user-interaktiv) — enklare backend-process.
- **2026-05-08:** Workspace Directory API för namn→email lookup (kräver workspace-admin-delegation, men robust).
- **2026-05-08:** Gmail API v1 via officiell SDK.
- **2026-05-08:** YAML-config för Google Cloud-nyckel (checkas INTE in).
- **2026-05-08:** Graceful degradation: saknas API-nyckel → skapa DRAFT med bara namn; API-fel → logg och gå vidare.
