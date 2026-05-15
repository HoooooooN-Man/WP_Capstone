#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export APP_ENV_FILE="${APP_ENV_FILE:-configs/webnews.env}"

DISPLAY_DATE="${1:-$(TZ=Asia/Seoul date +%F)}"
IDLE_TIMEOUT="${WEBNEWS_BATCH_IDLE_TIMEOUT:-10s}"
BATCH_SIZE="${WEBNEWS_BATCH_SIZE:-10}"
PUBLISH_EVENTS_KEEP="${WEBNEWS_PUBLISH_EVENTS_KEEP:-30}"

LOG_DIR="$ROOT_DIR/logs/webnews"
RUN_DIR="$ROOT_DIR/run"
LOCK_FILE="$RUN_DIR/webnews_daily_batch.lock"
LOG_FILE="$LOG_DIR/daily-batch-${DISPLAY_DATE}-$(TZ=Asia/Seoul date +%H%M%S).log"

mkdir -p "$LOG_DIR" "$RUN_DIR"
mkdir -p "$ROOT_DIR/data/webnews/current"
mkdir -p "$ROOT_DIR/data/webnews/staging"
mkdir -p "$ROOT_DIR/data/webnews/archive"

(
  flock -n 9 || {
    echo "[SKIP] webnews daily batch is already running"
    exit 1
  }

  {
    echo "============================================================"
    echo "[START] webnews daily batch"
    echo "============================================================"
    echo "[INFO] root_dir=$ROOT_DIR"
    echo "[INFO] app_env_file=$APP_ENV_FILE"
    echo "[INFO] display_date=$DISPLAY_DATE"
    echo "[INFO] idle_timeout=$IDLE_TIMEOUT"
    echo "[INFO] batch_size=$BATCH_SIZE"
    echo "[INFO] publish_events_keep=$PUBLISH_EVENTS_KEEP"
    echo "[INFO] started_at=$(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S %Z')"
    echo

    echo "------------------------------------------------------------"
    echo "[1/8] build webnews binaries"
    echo "------------------------------------------------------------"
    bash scripts/build_webnews_bins.sh
    echo

    echo "------------------------------------------------------------"
    echo "[2/8] prune before batch"
    echo "------------------------------------------------------------"
    ./bin/webnews_prune \
        --phase before \
        --display-date "$DISPLAY_DATE" \
        --reset-display-date
    echo

    echo "------------------------------------------------------------"
    echo "[3/8] schedule collect jobs"
    echo "------------------------------------------------------------"
    ./bin/webnews_scheduler --display-date "$DISPLAY_DATE"
    echo

    echo "------------------------------------------------------------"
    echo "[4/8] collect RSS items"
    echo "------------------------------------------------------------"
    ./bin/webnews_collector \
      --once \
      --idle-timeout "$IDLE_TIMEOUT" \
      --batch-size "$BATCH_SIZE"
    echo

    echo "------------------------------------------------------------"
    echo "[5/8] enrich raw items"
    echo "------------------------------------------------------------"
    ./bin/webnews_enricher \
      --once \
      --idle-timeout "$IDLE_TIMEOUT" \
      --batch-size "$BATCH_SIZE"
    echo

    echo "------------------------------------------------------------"
    echo "[6/8] finalize staging JSON"
    echo "------------------------------------------------------------"
    ./bin/webnews_finalizer --display-date "$DISPLAY_DATE"
    echo

    echo "------------------------------------------------------------"
    echo "[7/8] publish current JSON"
    echo "------------------------------------------------------------"
    ./bin/webnews_publish --display-date "$DISPLAY_DATE"
    echo

    echo "------------------------------------------------------------"
    echo "[8/8] prune after batch"
    echo "------------------------------------------------------------"
    ./bin/webnews_prune \
      --phase after \
      --display-date "$DISPLAY_DATE" \
      --trim-publish-events "$PUBLISH_EVENTS_KEEP"
    echo

    echo "------------------------------------------------------------"
    echo "[cleanup] remove old logs"
    echo "------------------------------------------------------------"
    find "$LOG_DIR" -type f -name "*.log" -mtime +7 -delete || true
    echo

    echo "============================================================"
    echo "[DONE] webnews daily batch"
    echo "============================================================"
    echo "[INFO] display_date=$DISPLAY_DATE"
    echo "[INFO] current_dir=$ROOT_DIR/data/webnews/current"
    echo "[INFO] finished_at=$(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S %Z')"
  } 2>&1 | tee -a "$LOG_FILE"

) 9>"$LOCK_FILE"