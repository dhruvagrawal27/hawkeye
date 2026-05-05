#!/usr/bin/env bash
# ------------------------------------------------------------
# download-artifacts.sh
# Downloads model files and synthetic data from GitHub Releases.
# Run this once after git clone before `docker compose up`.
#
# Usage:
#   bash scripts/download-artifacts.sh
# ------------------------------------------------------------
set -euo pipefail

REPO="dhruvagrawal27/hawkeye"
TAG="v1.0.0"
BASE_URL="https://github.com/${REPO}/releases/download/${TAG}"

ARTIFACTS_DIR="$(dirname "$0")/../backend/artifacts"
DATA_DIR="$(dirname "$0")/../backend/data"

mkdir -p "$ARTIFACTS_DIR" "$DATA_DIR"

echo "⬇  Downloading HAWKEYE model artifacts from GitHub Releases (${TAG})..."

download() {
  local file="$1"
  local dest="$2"
  if [ -f "$dest" ]; then
    echo "   ✓ Already exists: $dest (skipping)"
  else
    echo "   ↓ $file"
    curl -fL --progress-bar "${BASE_URL}/${file}" -o "$dest"
  fi
}

download "lgb_model_m1_full.txt"  "${ARTIFACTS_DIR}/lgb_model_m1_full.txt"
download "lgb_model_m2_full.txt"  "${ARTIFACTS_DIR}/lgb_model_m2_full.txt"
download "feature_config.json"    "${ARTIFACTS_DIR}/feature_config.json"
download "feature_stats.json"     "${ARTIFACTS_DIR}/feature_stats.json"
download "synthetic_events.jsonl" "${DATA_DIR}/synthetic_events.jsonl"

echo ""
echo "✅ All artifacts ready."
echo "   Run: docker compose up --build"
