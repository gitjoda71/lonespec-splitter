# Changelog

Alla anmärkningsvärda ändringar i detta projekt dokumenteras här.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioner enligt [SemVer](https://semver.org/lang/sv/).

## [Unreleased]

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
