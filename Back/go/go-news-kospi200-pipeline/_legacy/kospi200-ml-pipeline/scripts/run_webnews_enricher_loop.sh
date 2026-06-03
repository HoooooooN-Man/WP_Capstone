#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export APP_ENV_FILE="${APP_ENV_FILE:-configs/webnews.env}"
LOG_DIR="$ROOT_DIR/logs/webnews"
mkdir -p "$LOG_DIR"

while true; do
  echo "[$(date '+%F %T')] enricher start" >> "$LOG_DIR/supervisor.log"
  ./bin/webnews_enricher >> "$LOG_DIR/enricher.log" 2>&1 || true
  code=$?
  echo "[$(date '+%F %T')] enricher exited code=$code, restart in 10s" >> "$LOG_DIR/supervisor.log"
  sleep 10
done