# -----------------------------------------------------------
# download-artifacts.ps1
# Downloads model files and synthetic data from GitHub Releases.
# Run this once after git clone before `docker compose up`.
#
# Usage (from repo root):
#   .\scripts\download-artifacts.ps1
# -----------------------------------------------------------

$Repo    = "dhruvagrawal27/hawkeye"
$Tag     = "v1.0.0"
$BaseUrl = "https://github.com/$Repo/releases/download/$Tag"

$Root         = Split-Path $PSScriptRoot -Parent
$ArtifactsDir = Join-Path $Root "backend\artifacts"
$DataDir      = Join-Path $Root "backend\data"

New-Item -ItemType Directory -Force -Path $ArtifactsDir | Out-Null
New-Item -ItemType Directory -Force -Path $DataDir      | Out-Null

function Download-File($FileName, $DestPath) {
    if (Test-Path $DestPath) {
        Write-Host "  ✓ Already exists: $DestPath (skipping)" -ForegroundColor Green
    } else {
        Write-Host "  ↓ Downloading $FileName ..." -ForegroundColor Cyan
        $url = "$BaseUrl/$FileName"
        Invoke-WebRequest -Uri $url -OutFile $DestPath -UseBasicParsing
        Write-Host "    Saved to $DestPath" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "⬇  Downloading HAWKEYE model artifacts from GitHub Releases ($Tag)..." -ForegroundColor Yellow
Write-Host ""

Download-File "lgb_model_m1_full.txt"  (Join-Path $ArtifactsDir "lgb_model_m1_full.txt")
Download-File "lgb_model_m2_full.txt"  (Join-Path $ArtifactsDir "lgb_model_m2_full.txt")
Download-File "feature_config.json"    (Join-Path $ArtifactsDir "feature_config.json")
Download-File "feature_stats.json"     (Join-Path $ArtifactsDir "feature_stats.json")
Download-File "synthetic_events.jsonl" (Join-Path $DataDir      "synthetic_events.jsonl")

Write-Host ""
Write-Host "✅ All artifacts ready. Now run:" -ForegroundColor Green
Write-Host "   docker compose up --build" -ForegroundColor White
