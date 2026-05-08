# Changelog

Alla anmärkningsvärda ändringar i detta projekt dokumenteras här.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioner enligt [SemVer](https://semver.org/lang/sv/).

## [Unreleased]

## [0.2.0] — 2026-05-08

### Added
- **Gmail-drafting**: Automatisk skapning av Gmail-utkast för varje lönespec-mottagare.
- Google Workspace Directory API-integrering för namn → email-lookup.
- Google Workspace-admin setup-guide (`GMAIL_SETUP.md`).
- CLI-flaggor: `--with-gmail` och `--gmail-config <path>`.
- Config-file `gmail_config.yaml` för Google Cloud Service Account och Workspace-domän.
- Graceful degradation: saknas API-nyckel eller Directory API-lookup misslyckas → logg + hoppa över draft.

### Changed
- `requirements.txt` utökad med Google API-bibliotek (`google-auth`, `google-api-python-client`, `PyYAML`).

### Known limitations
- Gmail-drafting kräver Google Workspace-admin för API-setup + domain-wide delegation.
- Service Account-nyckel är känslig och får ej checkas in (redan i `.gitignore`).

## [0.1.1] — 2026-05-08

### Added
- **Kontek-layoutstöd**: keywordet `Mottagare` (med eller utan kolon) följt av namn på nästa rad.
- Stöd för formatet **`Efternamn, Förnamn`** (vanligt i Kontek/svenska lönesystem) — delas korrekt till förnamn/efternamn i filnamnet.
- Ny syntetisk fixture `fixture_kontek_3personer.pdf` + integration­stest.
- Fler ord på blocklistan (`Kontek`, `Crona`, `Löneperiod`, `Insatt`, `Sverige`, `Stockholm`, `Göteborg`, `Malmö`) så företagsnamn/rubriker inte plockas som personnamn.

### Changed
- `_split_log.txt` skrivs nu med **UTF-8 BOM** (`utf-8-sig`) så Notepad och äldre Windows-verktyg visar åäö rätt.
- Strategi 1 (keyword-match) hoppar förbi tomma rader när namnet står på rad 2 efter keywordet.

### Fixed
- Verifierat mot en riktig 23-sidig Kontek-lönespec: 23/23 personer får korrekt namn (tidigare 8/23).

## [0.1.0] — 2026-05-08

### Added
- Python-backend (`lonespec_splitter`) som splittar PDF + extraherar Förnamn/Efternamn/datum.
- Tre syntetiska test-fixtures (Visma-, Hogia-, generisk-layout).
- Acrobat folder-level JavaScript + Action Wizard-sequence.
- Windows installer (`install.ps1`).
- pytest unit + integration tests (40/40 grön).
- GitHub Actions CI (Windows+Linux × py3.11/3.12) + release-workflow.
- CLI: `python -m lonespec_splitter <input.pdf> <outdir>`.

### Known limitations
- OCR är best-effort (Tesseract-baserad). Sidor utan text → `OKAND_sidaN.pdf` om Tesseract saknas.
- macOS-installer saknas — manuella steg dokumenterade i INSTALL.md.
- Krypterade PDF:er avbryts med felmeddelande (ingen unlock-prompt).
- Acrobat-trigger kan i nyare DC-versioner blockera auto-launch — då skriver plugin ut en .bat-fil som användaren kör manuellt.
