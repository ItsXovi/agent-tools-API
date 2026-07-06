$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Is-StorePythonStub([string]$Path) {
    if (-not $Path) { return $true }
    $normalized = ($Path -replace '/', '\')
    return ($normalized -match '\\Microsoft\\WindowsApps\\python3?\.exe$')
}

function Test-PythonExe([string]$Path) {
    if (-not $Path -or -not (Test-Path $Path)) { return $false }
    if (Is-StorePythonStub $Path) { return $false }
    try {
        $version = & $Path -c "import sys; print(sys.version)" 2>$null
        return ($LASTEXITCODE -eq 0 -and $version)
    } catch {
        return $false
    }
}

function Find-Python {
    $candidates = [System.Collections.Generic.List[string]]::new()

    foreach ($root in @(
        "$env:LOCALAPPDATA\Python",
        "$env:LOCALAPPDATA\Programs\Python",
        "$env:ProgramFiles\Python"
    )) {
        if (-not (Test-Path $root)) { continue }
        Get-ChildItem $root -Recurse -Filter "python.exe" -ErrorAction SilentlyContinue |
            ForEach-Object { $candidates.Add($_.FullName) }
    }

    $winAppsPython = "$env:ProgramFiles\WindowsApps"
    if (Test-Path $winAppsPython) {
        Get-ChildItem $winAppsPython -Directory -Filter "PythonSoftwareFoundation.*" -ErrorAction SilentlyContinue |
            ForEach-Object {
                $exe = Join-Path $_.FullName "python.exe"
                if (Test-Path $exe) { $candidates.Add($exe) }
            }
    }

    foreach ($path in ($candidates | Select-Object -Unique)) {
        if (Test-PythonExe $path) { return $path }
    }
    return $null
}

$py = Find-Python

if (-not $py) {
    Write-Host ""
    Write-Host "Python 3 is NOT installed on this PC." -ForegroundColor Red
    Write-Host "(The Microsoft Store python.exe stub does not count.)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  Check: Add python.exe to PATH"
    Write-Host ""
    Write-Host "Disable Store aliases if needed:" -ForegroundColor Yellow
    Write-Host "  Settings > Apps > App execution aliases > OFF python.exe and python3.exe"
    Write-Host ""
    exit 1
}

Write-Host "Using Python: $py" -ForegroundColor Green
& $py --version

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    if (Test-Path ".venv") { Remove-Item ".venv" -Recurse -Force }
    & $py -m venv .venv
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        Write-Error "Failed to create .venv - is the venv module installed?"
    }
}

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
Write-Host "Installing dependencies..."
& $venvPy -m pip install --upgrade pip -q
& $venvPy -m pip install -r requirements.txt -q

Write-Host ""
Write-Host "PDF Toolkit API running at:" -ForegroundColor Green
Write-Host "  http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host ""

& $venvPy -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
