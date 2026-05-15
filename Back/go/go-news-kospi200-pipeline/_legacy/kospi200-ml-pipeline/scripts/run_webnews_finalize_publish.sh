#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p logs/webnews run

if [[ ! -x "$ROOT/bin/webnews_finalizer" || ! -x "$ROOT/bin/webnews_publish" ]]; then
  bash "$ROOT/scripts/build_webnews_bins.sh"
fi

LOCK_FILE="$ROOT/run/webnews_finalize_publish.lock"
LOG_FILE="$ROOT/logs/webnews/finalize-publish-$(date +%F).log"

DISPLAY_DATE="${1:-}"

if [[ -n "$DISPLAY_DATE" ]]; then
  FINALIZER_CMD="APP_ENV_FILE=configs/webnews.env '$ROOT/bin/webnews_finalizer' --display-date '$DISPLAY_DATE'"
  PUBLISH_CMD="APP_ENV_FILE=configs/webnews.env '$ROOT/bin/webnews_publish' --display-date '$DISPLAY_DATE'"
else
  FINALIZER_CMD="APP_ENV_FILE=configs/webnews.env '$ROOT/bin/webnews_finalizer'"
  PUBLISH_CMD="APP_ENV_FILE=configs/webnews.env '$ROOT/bin/webnews_publish'"
fi

flock -n "$LOCK_FILE" bash -lc "
  cd '$ROOT'
  echo \"[$(date '+%F %T')] finalize start\" >> '$LOG_FILE'
  $FINALIZER_CMD >> '$LOG_FILE' 2>&1
  echo \"[$(date '+%F %T')] publish start\" >> '$LOG_FILE'
  $PUBLISH_CMD >> '$LOG_FILE' 2>&1
  echo \"[$(date '+%F %T')] finalize/publish end\" >> '$LOG_FILE'
"