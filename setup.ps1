# One-time setup: create venv and install deps (does not start server)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-PythonExe([string]$Path) {
    if (-not $Path -or -not (Test-Path $Path)) { return $false }
    if ($Path -match "WindowsApps") { return $false }
    try {
        & $Path -c "import sys" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

$py = $null
if (Test-Path "$env:LOCALAPPDATA\Programs\Python") {
    Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Recurse -Filter "python.exe" -ErrorAction SilentlyContinue |
        ForEach-Object {
            if (-not $py -and (Test-PythonExe $_.FullName)) { $py = $_.FullName }
        }
}

if (-not $py) {
    Write-Error "Python not found. Install from https://www.python.org/downloads/ (check Add to PATH)."
}

Write-Host "Using: $py"
& $py -m venv .venv --clear
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Write-Host "Setup complete. Start server with: .\run.ps1"
