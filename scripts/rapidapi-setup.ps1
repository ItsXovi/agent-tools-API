# RapidAPI Hub setup helper — prepares clipboard + file picker, then prints 3 manual steps.
# Usage: .\scripts\rapidapi-setup.ps1

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$baseUrl = "https://agent-tools-api-production.up.railway.app"
$openApiPath = Join-Path $repoRoot "docs\rapidapi-openapi.json"
$studioUrl = "https://rapidapi.com/studio"

if (-not (Test-Path -LiteralPath $openApiPath)) {
    throw "OpenAPI file not found: $openApiPath"
}

# Base URL on clipboard for step 1 (Ctrl+V in Hub Listing > General > Base URL)
Set-Clipboard -Value $baseUrl

# Highlight the OpenAPI file in Explorer for step 2 upload
explorer.exe "/select,`"$openApiPath`""

Write-Host ""
Write-Host "=== RapidAPI setup (3 clicks) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Base URL copied to clipboard: $baseUrl"
Write-Host "OpenAPI file selected in Explorer: $openApiPath"
Write-Host ""
Write-Host "In RapidAPI Studio (opening now), complete these 3 steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1) Hub Listing > General > Base URL"
Write-Host "     Paste (Ctrl+V) the base URL, then click Save."
Write-Host ""
Write-Host "  2) Hub Listing > Definitions > CI/CD > Import OpenAPI"
Write-Host "     Upload docs\rapidapi-openapi.json (selected in Explorer), then confirm import."
Write-Host ""
Write-Host "  3) Hub Listing > Definitions > Security > New Scheme"
Write-Host "     Type: API Key | In: Header | Name: X-API-Key | Apply to all endpoints."
Write-Host ""
Write-Host "Done — your API is wired to production." -ForegroundColor Green
Write-Host ""

Start-Process $studioUrl
