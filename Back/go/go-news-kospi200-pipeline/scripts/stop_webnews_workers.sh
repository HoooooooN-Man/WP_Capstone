#!/usr/bin/env bash
set -euo pipefail

stop_by_pattern() {
  local label="$1"
  local pattern="$2"

  if pgrep -af "$pattern" >/dev/null 2>&1; then
    pkill -f "$pattern" || true
    echo "[OK] stopped $label"
  else
    echo "[SKIP] $label not running"
  fi
}

stop_by_pattern "collector supervisor" "scripts/run_webnews_collector_loop.sh"
stop_by_pattern "enricher supervisor" "scripts/run_webnews_enricher_loop.sh"
stop_by_pattern "html augmentor supervisor" "scripts/run_webnews_html_augmentor_loop.sh"

stop_by_pattern "webnews_collector binary" "bin/webnews_collector"
stop_by_pattern "webnews_enricher binary" "bin/webnews_enricher"
stop_by_pattern "webnews_html_augmentor binary" "bin/webnews_html_augmentor"