# Push MDA project to GitHub (run from repo root)
$ErrorActionPreference = "Stop"

$Gh = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $Gh)) {
    Write-Host "GitHub CLI not found. Install with: winget install GitHub.cli" -ForegroundColor Red
    exit 1
}

$RepoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $RepoRoot

function Test-GhAuth {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & $Gh auth status 2>&1 | Out-Null
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prev
    return $ok
}

if (-not (Test-GhAuth)) {
    Write-Host "Logging in to GitHub..." -ForegroundColor Cyan
    Write-Host "Follow the prompts and complete login in your browser." -ForegroundColor Yellow
    & $Gh auth login -h github.com -p https -w
    if ($LASTEXITCODE -ne 0) {
        Write-Host "GitHub login failed or was cancelled." -ForegroundColor Red
        exit 1
    }
}

$hasRemote = $false
$prev = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
git remote get-url origin 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) { $hasRemote = $true }
$ErrorActionPreference = $prev

if (-not $hasRemote) {
    Write-Host "Creating public repo 'MDA' and pushing..." -ForegroundColor Cyan
    & $Gh repo create MDA --public --source=. --remote=origin --push
} else {
    Write-Host "Pushing to origin/main..." -ForegroundColor Cyan
    git push -u origin main
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Push failed. Check errors above." -ForegroundColor Red
    exit 1
}

Write-Host "Done. Repository pushed to GitHub." -ForegroundColor Green
