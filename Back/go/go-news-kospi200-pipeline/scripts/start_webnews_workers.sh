#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export APP_ENV_FILE="${APP_ENV_FILE:-configs/webnews.env}"
LOG_DIR="$ROOT_DIR/logs/webnews"
mkdir -p "$LOG_DIR"

start_if_missing() {
  local name="$1"
  local script="$2"

  if pgrep -af "$script" >/dev/null 2>&1; then
    echo "[SKIP] $name supervisor already running"
    pgrep -af "$script"
    return 0
  fi

  nohup bash "$script" >/dev/null 2>&1 &
  sleep 1

  if pgrep -af "$script" >/dev/null 2>&1; then
    echo "[OK] started $name supervisor"
    pgrep -af "$script"
  else
    echo "[ERR] failed to start $name supervisor"
    return 1
  fi
}

start_if_missing "webnews_collector" "$ROOT_DIR/scripts/run_webnews_collector_loop.sh"
start_if_missing "webnews_enricher" "$ROOT_DIR/scripts/run_webnews_enricher_loop.sh"
start_if_missing "webnews_html_augmentor" "$ROOT_DIR/scripts/run_webnews_html_augmentor_loop.sh"

echo
echo "[INFO] running binaries"
pgrep -af "bin/webnews_collector" || true
pgrep -af "bin/webnews_enricher" || true
pgrep -af "bin/webnews_html_augmentor" || true