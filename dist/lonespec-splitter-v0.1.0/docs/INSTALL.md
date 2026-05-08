# Installation — lonespec-splitter

## Förutsättningar

| Kravet | Var? |
|---|---|
| Windows 10/11 | — |
| Adobe Acrobat **Pro** DC (Reader funkar inte — saknar JavaScript) | Installerat |
| Python 3.11 eller nyare | https://www.python.org/downloads/ — bocka **"Add python.exe to PATH"** vid installation. |
| (Valfritt) Tesseract OCR + svenskt språkdata | https://github.com/UB-Mannheim/tesseract/wiki — för OCR-fallback |

## Snabbstart (rekommenderat)

1. Hämta senaste releasen från [Releases-sidan](https://github.com/gitjoda71/lonespec-splitter/releases) — fil `lonespec-splitter-v0.1.0.zip`.
2. Packa upp ZIP:en till en mapp du minns var du la, t.ex. `C:\Tools\lonespec-splitter\`.
3. Högerklicka på `install.ps1` → **"Kör med PowerShell"**.
4. När scriptet skriver "Installation klar!" — **starta om Adobe Acrobat Pro DC**.

> Om PowerShell vägrar köra scriptet: starta PowerShell som administratör och kör
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Sen `cd` till mappen och kör `.\install.ps1`.

## Verifiera installationen

1. Starta Adobe Acrobat Pro DC.
2. Öppna en samlad lönespec-PDF (eller en av test-fixturerna i `tests/fixtures/`).
3. Klicka **Verktyg → Action Wizard → "Splitta lönespec"**, eller välj menyposten **"Splitta lönespec…"** under **Verktyg**.
4. En dialogruta ber dig välja utdatamapp. Skriv in t.ex. `C:\Users\<du>\Desktop\splittade`.
5. Klart! Delfilerna + `_split_log.txt` hamnar i den mappen.

## Använda från kommandoraden (utan Acrobat)

```powershell
cd "C:\Tools\lonespec-splitter"
python -m lonespec_splitter "C:\path\till\samlad.pdf" "C:\path\till\utdata\"
```

Flaggor:
- `--ocr` — använd OCR-fallback för bildbaserade sidor (kräver Tesseract).
- `--quiet` — minimal stdout.

Exit-koder: `0` OK, `1` generic, `2` lösenordsskyddad PDF, `3` indata saknas, `4` utdatamapp inte skrivbar.

## Manuell installation (om PowerShell-scriptet misslyckas)

1. **Python-paketet:**
   ```powershell
   cd "C:\Tools\lonespec-splitter"
   python -m pip install -e .
   ```
2. **Acrobat JS-skript:**
   - Kopiera `src\acrobat\lonespec_splitter.js` till
     `%APPDATA%\Adobe\Acrobat\DC\JavaScripts\`
3. **Action Wizard sequence:**
   - Kopiera `src\acrobat\Splitta lonespec.sequ` till
     `%APPDATA%\Adobe\Acrobat\DC\Sequences\`
4. Starta om Acrobat.

## Avinstallera

Radera följande filer:

- `%APPDATA%\Adobe\Acrobat\DC\JavaScripts\lonespec_splitter.js`
- `%APPDATA%\Adobe\Acrobat\DC\Sequences\Splitta lonespec.sequ`

Och valfritt:

```powershell
python -m pip uninstall lonespec-splitter
```

## macOS (manuell, v0.1)

Vi har ingen automatisk installer för macOS i v0.1. Manuella steg:

1. Installera Python från python.org eller via Homebrew.
2. `pip install -e .` i den uppackade mappen.
3. Kopiera Acrobat-skripten till
   `~/Library/Application Support/Adobe/Acrobat/DC/JavaScripts/`
   resp. `…/Sequences/`.

## Felsökning

| Symptom | Sannolik orsak | Åtgärd |
|---|---|---|
| Action menyn syns inte i Acrobat | JS-fil ligger fel/Acrobat ej omstartad | Verifiera att `lonespec_splitter.js` ligger i `JavaScripts`-mappen, starta om Acrobat. |
| `app.alert: Python hittades inte` | Python ej i PATH | Kör `python --version` i PowerShell. Om "command not found": ominstallera Python med "Add to PATH" ibockad. |
| Ingen utdata i mappen, bara `_lonespec_stderr.txt` | Backend kraschade | Öppna `_lonespec_stderr.txt` — vanligtvis "PDF lösenordsskyddad" eller "modul saknas". |
| Filerna heter `OKAND_sidaN.pdf` | Layouten kände inte igen — fallback aktiverad | Öppna `_split_log.txt` och se vilken regel som missade. Skicka gärna en (avidentifierad) testfil som issue. |
| Acrobat blockerar auto-start av .bat | Säkerhetspolicy | Öppna utdatamappen och dubbelklicka `_run_lonespec_splitter.bat` manuellt. |
