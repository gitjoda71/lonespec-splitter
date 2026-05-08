<#
    install.ps1 — Installerar lonespec-splitter på Windows.

    Körs:
        Högerklick → "Kör med PowerShell"
    eller från ett PowerShell-fönster:
        cd <unpacked-zip>
        .\install.ps1

    Stegen:
      1. Verifiera Python ≥ 3.11.
      2. pip install -e . (eller från requirements.txt).
      3. Kopiera lonespec_splitter.js → %APPDATA%\Adobe\Acrobat\DC\JavaScripts\
      4. Kopiera "Splitta lonespec.sequ" → %APPDATA%\Adobe\Acrobat\DC\Sequences\
      5. Skriver ut nästa-steg-meddelande.
#>

param(
    [switch]$NoPip
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    $msg" -ForegroundColor Yellow }

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1) Python check
Write-Step "Verifierar Python"
try {
    $ver = & python --version 2>&1
    if ($ver -notmatch "Python 3\.(1[1-9]|[2-9]\d)") {
        Write-Warn "Hittade '$ver' — vi rekommenderar Python 3.11 eller nyare."
    } else {
        Write-OK $ver
    }
} catch {
    Write-Host "FEL: Python hittades inte i PATH. Installera från https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# 2) Pip install
if (-not $NoPip) {
    Write-Step "Installerar Python-beroenden"
    Push-Location $root
    try {
        if (Test-Path "pyproject.toml") {
            & python -m pip install --upgrade pip --quiet
            & python -m pip install -e . --quiet
        } elseif (Test-Path "requirements.txt") {
            & python -m pip install -r requirements.txt --quiet
        } else {
            Write-Warn "Hittade varken pyproject.toml eller requirements.txt — hoppar över pip install."
        }
        Write-OK "Python-paket installerade."
    } finally {
        Pop-Location
    }
}

# 3) Hitta Acrobat-version under %APPDATA%\Adobe\Acrobat\
$acrobatRoot = Join-Path $env:APPDATA "Adobe\Acrobat"
if (-not (Test-Path $acrobatRoot)) {
    Write-Host "FEL: Hittar inte $acrobatRoot — är Adobe Acrobat installerat?" -ForegroundColor Red
    exit 1
}

# Plocka senaste version-mapp (DC, 2017, 2020 etc.)
$verDirs = Get-ChildItem -Path $acrobatRoot -Directory |
    Where-Object { $_.Name -match "^(DC|20\d\d)$" } |
    Sort-Object Name -Descending
if (-not $verDirs) {
    Write-Host "FEL: Hittade ingen Acrobat-versionmapp under $acrobatRoot." -ForegroundColor Red
    exit 1
}
$acrobatVer = $verDirs[0]
Write-OK "Använder Acrobat-version: $($acrobatVer.Name)"

$jsDir  = Join-Path $acrobatVer.FullName "JavaScripts"
$seqDir = Join-Path $acrobatVer.FullName "Sequences"
New-Item -ItemType Directory -Force -Path $jsDir,$seqDir | Out-Null

# 4) Kopiera filer
Write-Step "Kopierar Acrobat-skript"
$srcJs  = Join-Path $root "src\acrobat\lonespec_splitter.js"
$srcSeq = Join-Path $root "src\acrobat\Splitta lonespec.sequ"
if (-not (Test-Path $srcJs))  { Write-Host "FEL: $srcJs saknas" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $srcSeq)) { Write-Host "FEL: $srcSeq saknas" -ForegroundColor Red; exit 1 }
Copy-Item -Force $srcJs  (Join-Path $jsDir "lonespec_splitter.js")
Copy-Item -Force $srcSeq (Join-Path $seqDir "Splitta lonespec.sequ")
Write-OK "Kopierade JS-skript till $jsDir"
Write-OK "Kopierade Action Wizard till $seqDir"

# 5) Klart!
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Installation klar!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host " Nästa steg:" -ForegroundColor White
Write-Host "  1) Starta om Adobe Acrobat Pro DC." -ForegroundColor White
Write-Host "  2) Öppna en samlad lönespec-PDF." -ForegroundColor White
Write-Host "  3) Verktyg → Action Wizard → 'Splitta lönespec'." -ForegroundColor White
Write-Host "     (eller menyn 'Splitta lönespec…' under Verktyg)." -ForegroundColor White
Write-Host ""
