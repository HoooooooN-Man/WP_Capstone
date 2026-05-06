#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p logs/webnews run

if [[ ! -x "$ROOT/bin/webnews_scheduler" ]]; then
  bash "$ROOT/scripts/build_webnews_bins.sh"
fi

LOCK_FILE="$ROOT/run/webnews_scheduler.lock"
LOG_FILE="$ROOT/logs/webnews/scheduler-$(date +%F).log"

flock -n "$LOCK_FILE" bash -lc "
  cd '$ROOT'
  echo \"[$(date '+%F %T')] scheduler start\" >> '$LOG_FILE'
  APP_ENV_FILE=configs/webnews.env '$ROOT/bin/webnews_scheduler' >> '$LOG_FILE' 2>&1
  echo \"[$(date '+%F %T')] scheduler end\" >> '$LOG_FILE'
"