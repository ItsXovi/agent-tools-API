# Downloads and installs CPython 3.13 (official python.org build)
# Run in PowerShell:  .\install-python.ps1

$ErrorActionPreference = "Stop"

$installDir = "$env:LOCALAPPDATA\Programs\Python\Python313"
$pythonExe = Join-Path $installDir "python.exe"

if (Test-Path $pythonExe) {
    Write-Host "Python already installed at: $pythonExe" -ForegroundColor Green
    & $pythonExe --version
    exit 0
}

Write-Host "Downloading Python 3.13 installer from python.org..."
$installer = Join-Path $env:TEMP "python-3.13.2-amd64.exe"
$urls = @(
    "https://www.python.org/ftp/python/3.13.2/python-3.13.2-amd64.exe",
    "https://www.python.org/ftp/python/3.13.1/python-3.13.1-amd64.exe"
)

$ok = $false
foreach ($url in $urls) {
    try {
        Write-Host "Trying $url"
        Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
        $ok = $true
        break
    } catch {
        Write-Host "Failed: $_"
    }
}

if (-not $ok) {
    Write-Host ""
    Write-Host "Auto-download failed. Install manually:" -ForegroundColor Yellow
    Write-Host "  1. Open https://www.python.org/downloads/"
    Write-Host "  2. Download Python 3.13 for Windows"
    Write-Host "  3. Run installer — CHECK 'Add python.exe to PATH'"
    Write-Host "  4. Then run: .\run.ps1"
    exit 1
}

Write-Host "Installing Python (this may take a minute)..."
# Per-user install, add to PATH, include pip
$args = @(
    "/passive",
    "InstallAllUsers=0",
    "PrependPath=1",
    "Include_pip=1",
    "Include_test=0"
)
$proc = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru

if ($proc.ExitCode -ne 0 -and $proc.ExitCode -ne 3010) {
    Write-Warning "Installer exit code: $($proc.ExitCode). Python may still have installed."
}

Start-Sleep -Seconds 2

if (Test-Path $pythonExe) {
    Write-Host ""
    Write-Host "Success! Python installed:" -ForegroundColor Green
    & $pythonExe --version
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. CLOSE this PowerShell window and open a NEW one"
    Write-Host "  2. cd C:\Users\gdick\agent-tools-api"
    Write-Host "  3. .\run.ps1"
} else {
    Write-Host ""
    Write-Host "Installer finished but python.exe not found at expected path." -ForegroundColor Yellow
    Write-Host "Install manually from https://www.python.org/downloads/"
    Write-Host "Make sure to check: Add python.exe to PATH"
}
