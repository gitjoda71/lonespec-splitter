# lonespec-splitter

Adobe Acrobat Pro-plugin som splittar en flersidig lönespec-PDF till en fil per person, med automatisk namnsättning `Förnamn Efternamn YYYY-MM-DD.pdf`.

> **Status:** v0.1.0 — första körbara versionen. Stöder textbaserade PDF:er från Visma/Hogia-liknande layouter. OCR-fallback är best-effort.

---

## Vad gör det?

Du har en samlad PDF med t.ex. 20 lönespecar i (en sida per person, eller flera sidor per person). Du vill ha 20 separata PDF:er, en per anställd, döpta efter mottagare och utbetalningsdatum.

Det här plugin-paketet gör det åt dig — antingen från Adobe Acrobat Pro DC via en knapp/Action, eller från kommandoraden.

## Snabbstart (CLI)

```powershell
cd "C:\0-dropbox\Dropbox\1oels dokument\Antigravity\Acrobat pro"
pip install -r requirements.txt
python -m lonespec_splitter "C:\path\till\samlad.pdf" "C:\path\till\utdata\"
```

## Snabbstart (Acrobat Pro DC)

1. Ladda ner senaste releasen från [Releases](https://github.com/gitjoda71/lonespec-splitter/releases).
2. Kör `install.ps1` (Windows PowerShell, högerklick → Kör med PowerShell).
3. Starta om Acrobat Pro DC.
4. Öppna en samlad lönespec-PDF.
5. **Verktyg → Action Wizard → "Splitta lönespec"**.

Detaljerad guide: [INSTALL.md](docs/INSTALL.md).

## Arkitektur

Hybrid: lättviktig Acrobat JavaScript-trigger + Python-backend. Se [ROADMAP.md](ROADMAP.md) för motivering och alternativ som övervägdes.

## Utveckling

```powershell
cd "C:\0-dropbox\Dropbox\1oels dokument\Antigravity\Acrobat pro"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest
```

## Licens

MIT — se [LICENSE](LICENSE).
