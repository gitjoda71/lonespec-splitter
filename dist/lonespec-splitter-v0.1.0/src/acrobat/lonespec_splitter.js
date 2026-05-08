/* lonespec_splitter.js
 * Folder-level JavaScript för Adobe Acrobat Pro DC.
 *
 * Installation: kopiera denna fil till
 *   %APPDATA%\Adobe\Acrobat\DC\JavaScripts\
 * och starta om Acrobat. Då blir menyposterna under
 *   Verktyg → Action Wizard → "Splitta lönespec"
 * tillgängliga (eller via Avancerat → Splitta lönespec…).
 *
 * Tekniskt:
 *   - Använder app.trustedFunction så vi får anropa privilegierade API:er.
 *   - Sparar aktivt dokument till en temp-fil (originalet ändras inte).
 *   - Ber användaren välja utdatamapp.
 *   - Anropar Python-backend via app.launchURL → cmd.exe / open.
 *
 * Kräver att Python-paketet "lonespec-splitter" är installerat
 * (system-wide eller i en venv vars python.exe ligger i PATH).
 */

// ============================================================================
//  Konfiguration — kan editeras av användaren
// ============================================================================

// Kommando som kör backend. {input} och {output} expanderas.
// På Windows: använd standardpython i PATH.
// Sätt absolut path till python.exe här om du har en specifik venv.
var LONESPEC_PYTHON = "python";
var LONESPEC_MODULE = "lonespec_splitter";

// ============================================================================

(function () {
    "use strict";

    function _shellQuote(s) {
        // Acrobats JS-engine är ES3-aktig — undvik moderna features.
        // Windows: omslut i dubbla citattecken, escape:a inre " som \".
        return '"' + String(s).replace(/"/g, '\\"') + '"';
    }

    /** Bygg .bat-fil i temp som kör Python-backend och pipar utdata till logg. */
    function _writeBatFile(input, output) {
        var bat = "@echo off\r\n" +
                  "chcp 65001 > nul\r\n" +
                  "setlocal\r\n" +
                  "set PYTHONIOENCODING=utf-8\r\n" +
                  _shellQuote(LONESPEC_PYTHON) + " -m " + LONESPEC_MODULE + " " +
                  _shellQuote(input) + " " + _shellQuote(output) +
                  " > " + _shellQuote(output + "\\_lonespec_stdout.txt") +
                  " 2> " + _shellQuote(output + "\\_lonespec_stderr.txt") + "\r\n" +
                  "echo EXIT=%ERRORLEVEL% >> " + _shellQuote(output + "\\_lonespec_stdout.txt") + "\r\n" +
                  "endlocal\r\n";
        var batPath = output + "\\_run_lonespec_splitter.bat";
        // Använd Doc.createDataObject? Nej — vi måste skriva till disk.
        // Acrobat har inte direkt fs.writeFile, men vi kan använda
        // util.printd-tricket eller — enklare — låt JS hoppa över .bat och
        // anropa cmd.exe direkt med /c "...".
        return null; // se _runBackend nedan
    }

    /** Spara aktivt dokument till en temp-PDF utan att ändra originalet. */
    function _saveActiveDocToTemp(doc) {
        // util.printd → unik temp-fil
        var stamp = util.printd("yyyymmdd_HHMMss", new Date());
        // Försök placera i samma mapp som originalet, fallback användarens
        // dokumentmapp.
        var dir = (doc.path || "").replace(/\/[^/]+$/, "");
        var tempName = "_lonespec_input_" + stamp + ".pdf";
        var tempPath = dir
            ? dir + "/" + tempName
            : "/c/Users/Public/" + tempName;

        // saveAs är privilegierad → måste ligga i trustedFunction
        doc.saveAs({
            cPath: tempPath,
            bCopy: true,           // ändra inte originalet
            bPromptToOverwrite: false
        });
        return tempPath;
    }

    /** Be användaren välja utdatamapp. v0.1: använd app.response för en path. */
    function _askOutputDir(defaultDir) {
        var msg = "Skriv in fullständig sökväg till mapp där delfilerna ska sparas.\n\n" +
                  "Exempel: C:\\Users\\Joel\\Desktop\\lonespecar\n\n" +
                  "Mappen skapas om den inte finns.";
        var resp = app.response({
            cQuestion: msg,
            cTitle: "Splitta lönespec — välj utdatamapp",
            cDefault: defaultDir || ""
        });
        if (resp === null) return null;
        return resp.replace(/^\s+|\s+$/g, "");
    }

    /** Konvertera Windows-path C:\foo\bar → /c/foo/bar (Acrobat-style). */
    function _winPathToAcrobat(p) {
        if (!p) return p;
        // Ersätt backslash med slash, "C:" → "/c"
        var s = p.replace(/\\/g, "/");
        var m = s.match(/^([A-Za-z]):(.*)$/);
        if (m) s = "/" + m[1].toLowerCase() + m[2];
        return s;
    }

    /** Konvertera Acrobat-style /c/foo → Windows C:\foo. */
    function _acrobatPathToWin(p) {
        if (!p) return p;
        var m = p.match(/^\/([a-zA-Z])\/(.*)$/);
        if (m) return m[1].toUpperCase() + ":\\" + m[2].replace(/\//g, "\\");
        return p.replace(/\//g, "\\");
    }

    /** Trigga backend via app.launchURL till en cmd-rad. */
    function _runBackend(inputWinPath, outputWinPath) {
        // Skapa output-mappen via privilegierat call:
        // det går inte direkt från JS — vi förlitar oss på att Python skapar den.
        // Bygg cmd-rad. cmd.exe /c "<cmd>" — tipsa Acrobat att starta extern process.

        // Acrobat tillåter inte godtyckliga app.launchURL till cmd.exe utan
        // PostScript-tillit. Men i en folder-level (privileged) kontext kan vi
        // använda app.execMenuItem? Nej. Det säkraste sättet i v0.1 är
        // **trustedFunction + Net.Discovery / SOAP är borta i moderna Acrobat**.
        //
        // Praktisk lösning: vi använder app.launchURL("cmd:/c \"...\"") vilket
        // *fungerar i Acrobat Pro DC* när skriptet ligger som folder-level
        // (privilegierat) JavaScript och användaren explicit aktiverat
        // "Tillåt högprivilegierade åtgärder" om så krävs.
        //
        // Kommandot:
        var cmd = LONESPEC_PYTHON + " -m " + LONESPEC_MODULE +
                  " " + _shellQuote(inputWinPath) + " " + _shellQuote(outputWinPath);

        // Skapa wrapper bat via writeFile? Acrobat saknar fs. Workaround:
        // använd app.launchURL med "file://"-protokoll fungerar inte här.
        //
        // Lösning som funkar i praktiken: vi använder "cmd.exe /c start ..."
        // via app.launchURL("cmd:/c ...") — protokoll-handlern på Windows.
        // Tyvärr har Adobe i nyare DC-versioner låst app.launchURL till http(s).
        //
        // Robust väg framåt (verifierad med Pro DC ≥ 2020):
        //   1. Skriv ut en .bat till outputmappen via Doc.createDataObject +
        //      Doc.exportDataObject (skickar binär till disk).
        //   2. app.launchURL("file:///<bat-path>") öppnar batchen.
        //
        // För enkelhetens skull i v0.1 dokumenterar vi att användaren alltid
        // kan dubbelklicka den genererade .bat-filen om auto-launch nekas.

        // Skapa .bat-innehåll
        var batContent = "@echo off\r\n" +
                         "chcp 65001 > nul\r\n" +
                         "set PYTHONIOENCODING=utf-8\r\n" +
                         cmd + "\r\n" +
                         "if errorlevel 1 (\r\n" +
                         "  echo Fel uppstod, se _lonespec_stderr.txt 1>&2\r\n" +
                         "  pause\r\n" +
                         ")\r\n";

        var batRel = "_run_lonespec_splitter.bat";
        var batAbs = outputWinPath + "\\" + batRel;

        // Skriv via Doc-mekanism
        try {
            this.createDataObject({
                cName: batRel,
                cValue: batContent,
                cMIMEType: "application/octet-stream"
            });
            this.exportDataObject({
                cName: batRel,
                cDIPath: _winPathToAcrobat(batAbs)
            });
        } catch (e) {
            app.alert(
                "Kunde inte skriva ut bat-filen.\n\n" +
                "Kör manuellt från cmd:\n  " + cmd + "\n\nFel: " + e
            );
            return false;
        }

        // Försök starta batchen
        try {
            app.launchURL("file:///" + batAbs.replace(/\\/g, "/"), true);
        } catch (e) {
            app.alert(
                "Plugin har skrivit en bat-fil till:\n" + batAbs + "\n\n" +
                "Dubbelklicka den för att starta splittringen.\n\n" +
                "(Acrobat blockerade auto-start: " + e + ")"
            );
            return true;
        }
        return true;
    }

    /** Huvudfunktion — anropas från Action eller meny. */
    var lonespecSplit = app.trustedFunction(function () {
        app.beginPriv();
        try {
            var doc = app.activeDocs && app.activeDocs.length
                ? app.activeDocs[0]
                : null;
            if (!doc) {
                app.alert("Öppna en samlad lönespec-PDF först.");
                return;
            }

            // Säkerställ att doc har en path (annars: be användaren spara först)
            if (!doc.path) {
                app.alert(
                    "Spara dokumentet på disk innan du splittar.\n" +
                    "(Ingen path-info → kan inte hitta filen för Python.)"
                );
                return;
            }

            // 1) Be användaren välja utdatamapp
            var defaultDir = _acrobatPathToWin(doc.path).replace(/\\[^\\]+$/, "") +
                             "\\splittade-lonespecar";
            var outDirWin = _askOutputDir(defaultDir);
            if (outDirWin === null || outDirWin === "") {
                return;  // avbruten
            }

            // 2) Spara aktivt dokument till temp så Python kan läsa det
            //    (Acrobat kan ha det öppet med write-lock — copy är säkrast)
            var inputAcrobat = _saveActiveDocToTemp(doc);
            var inputWin = _acrobatPathToWin(inputAcrobat);

            // 3) Kör backend
            var ok = _runBackend.call(doc, inputWin, outDirWin);
            if (ok) {
                app.alert(
                    "Lönespec-splitter startad.\n\n" +
                    "Utdata sparas i:\n  " + outDirWin + "\n\n" +
                    "När jobbet är klart hittar du delfilerna + _split_log.txt där."
                );
            }
        } catch (e) {
            app.alert("Oväntat fel: " + e + "\n\nStack: " + (e.stack || "(saknas)"));
        } finally {
            app.endPriv();
        }
    });

    // Exponera till Action Wizard:
    // Action-sekvensen anropar denna globala funktion.
    global.lonespecSplit = lonespecSplit;

    // Lägg till menypunkt under "Avancerat" så användaren kan trigga manuellt
    // utan att gå via Action Wizard.
    try {
        app.addMenuItem({
            cName: "Splitta lönespec…",
            cParent: "Tools",
            cExec: "global.lonespecSplit();",
            nPos: 0
        });
    } catch (e) {
        // addMenuItem kan kräva privilegierat läge på vissa versioner
    }

    console.println("[lonespec-splitter] folder-level script laddat");
})();
