# Push MDA project to GitHub (run from repo root)
$ErrorActionPreference = "Stop"

$Gh = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $Gh)) {
    Write-Host "GitHub CLI not found. Install with: winget install GitHub.cli" -ForegroundColor Red
    exit 1
}

$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

& $Gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Logging in to GitHub (browser will open)..." -ForegroundColor Cyan
    & $Gh auth login -h github.com -p https -w
}

if (-not (git remote get-url origin 2>$null)) {
    Write-Host "Creating public repo 'MDA' and pushing..." -ForegroundColor Cyan
    & $Gh repo create MDA --public --source=. --remote=origin --push
} else {
    Write-Host "Pushing to origin/main..." -ForegroundColor Cyan
    git push -u origin main
}

Write-Host "Done." -ForegroundColor Green
