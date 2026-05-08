# SPEC — Kravspecifikation lonespec-splitter v0.1.0

## 1. Funktionella krav

### F1. Split
- F1.1 Acceptera en flersidig PDF-fil som indata.
- F1.2 Producera en utdata-PDF per "lönespec" (= 1 person, 1 lönetillfälle).
- F1.3 Hantera fall där en lönespec sträcker sig över ≥ 2 sidor — gruppera korrekt.
- F1.4 Bevara originalets sidlayout och inbäddade fonter (ingen omsättning).

### F2. Namnsättning
- F2.1 Filnamn: `Förnamn Efternamn YYYY-MM-DD.pdf`.
- F2.2 Datum = utbetalningsdatum/lönedatum extraherat från sidans text.
- F2.3 Vid lyckad extraktion: använd det extraherade namnet och datumet.
- F2.4 Vid misslyckad extraktion: fallback-namn `OKAND_sidaN.pdf` (där N = ursprunglig sidnummer i indata).
- F2.5 Sanera filnamn (otillåtna tecken `\ / : * ? " < > |` ersätts med `_`).
- F2.6 Bevara svenska tecken å/ä/ö/Å/Ä/Ö (UTF-8 NFC).
- F2.7 Vid namnkrock: lägg till suffix `_1`, `_2`, … före `.pdf`.
- F2.8 Maxlängd 120 tecken (inkl. extension), trunkera namn-delen om nödvändigt.

### F3. Loggning
- F3.1 Skriv `_split_log.txt` i utdatamappen efter varje körning.
- F3.2 Logga: indata-sökväg, antal sidor, antal grupper, varje utdatafil, eventuella fel/varningar, tidsstämpel.
- F3.3 Om en grupp inte kunde parsas: logga vilken sida + vilken regel som misslyckades.

### F4. UX i Acrobat
- F4.1 Användaren ska kunna trigga jobbet via Action Wizard ("Splitta lönespec").
- F4.2 Användaren ska få välja utdatamapp via dialogruta.
- F4.3 Slutmeddelande: `app.alert` med "X filer skapade i <mapp>. Y varningar (se _split_log.txt)."
- F4.4 Vid fel: tydligt felmeddelande med första felraden från loggen.

### F5. Robusthet
- F5.1 Tolerera flera olika layouter (Visma, Hogia, Fortnox, generisk).
- F5.2 Fallback till OCR (Tesseract `-l swe`) om sidan saknar extraherbar text.
- F5.3 Om OCR saknas på systemet: graceful degradation → `OKAND_sidaN.pdf`, logga.
- F5.4 Krypterade PDF:er: avbryt med tydligt fel ("PDF:en är lösenordsskyddad — lås upp först").
- F5.5 Inga icke-fångade exceptions får läcka till användaren — wrappa main i try/except.

### F6. Standalone CLI
- F6.1 `python -m lonespec_splitter <input.pdf> <outdir> [--ocr]` ska fungera utan Acrobat.
- F6.2 `--help` listar alla flaggor.
- F6.3 Exit-koder: 0 OK, 1 generic error, 2 encrypted, 3 invalid input, 4 outdir not writable.

## 2. Icke-funktionella krav

### N1. Prestanda
- 20-sidig PDF ska splittas på < 10 sekunder utan OCR (på modern Windows-laptop).
- Med OCR: ingen hård gräns i v0.1, men progressrapportering var 5:e sida.

### N2. Plattform
- **Primär:** Windows 10/11 + Acrobat Pro DC + Python 3.11/3.12.
- **CI-stöd:** Linux (för pytest), inte produktionsmål för v0.1.
- **macOS:** dokumenterad manuell installation, men ingen installer-script i v0.1.

### N3. Säkerhet & integritet
- All bearbetning sker lokalt — ingen nätverkstrafik.
- Inga persondata committeras till repo. Alla fixtures är syntetiska.
- Logfilen sparas i utdatamappen (inte temp), så användaren har full kontroll.

### N4. Underhållbarhet
- Python-koden följer PEP 8 (verifieras med `ruff` om installerat).
- Type hints på publika funktioner.
- Docstrings på svenska för domänlogik (parser, layout-detektion).

## 3. Avgränsningar (out of scope för v0.1.0)

- ❌ Stöd för andra dokumenttyper än lönespec (fakturor, intyg etc.).
- ❌ E-postning av PDF:erna efter split.
- ❌ Krypterad PDF-output med olika lösenord per mottagare.
- ❌ Drag-och-släpp av flera samlings-PDF:er samtidigt.
- ❌ Konfigurerbara filnamnsmallar (kommer i v0.2).
- ❌ macOS installer-script.

## 4. Acceptanskriterier för release

1. Alla 3 fixture-PDF:er splittas med 100 % korrekt namngivning av Förnamn Efternamn + datum.
2. Manuell körning i Acrobat Pro DC: end-to-end utan handpåläggning.
3. INSTALL.md kan följas av en icke-utvecklare på Windows och leder till fungerande Action.
4. pytest grön i GitHub Actions på senaste commit på `main`.
5. Release v0.1.0 publicerad på GitHub med ZIP-artefakt.

## 5. Versionering

- SemVer: MAJOR.MINOR.PATCH.
- v0.1.0 = första funktionella release.
- v0.x.y = pre-1.0, breaking changes tillåtna.
- v1.0.0 = stabilt API + macOS-installer + dokumenterad konfiguration.
