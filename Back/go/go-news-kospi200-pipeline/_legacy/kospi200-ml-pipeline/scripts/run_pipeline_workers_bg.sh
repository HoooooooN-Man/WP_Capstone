#!/usr/bin/env bash
set -euo pipefail

cd ~/workspace/WP_Capstone/Back/go/go-news-kospi200-pipeline
mkdir -p logs

start_worker() {
  local name="$1"
  local cmd="$2"
  local pidfile="logs/${name}.pid"
  local logfile="logs/${name}.log"

  if [[ -f "$pidfile" ]]; then
    local oldpid
    oldpid="$(cat "$pidfile" 2>/dev/null || true)"
    if [[ -n "${oldpid:-}" ]] && kill -0 "$oldpid" 2>/dev/null; then
      echo "$name already running pid=$oldpid"
      return 0
    fi
  fi

  nohup bash -lc "$cmd" >> "$logfile" 2>&1 &
  echo $! > "$pidfile"
  echo "$name started pid=$(cat "$pidfile")"
}

start_worker "matcher" "cd ~/workspace/WP_Capstone/Back/go/go-news-kospi200-pipeline && go run ./cmd/matcher"
start_worker "aggregator" "cd ~/workspace/WP_Capstone/Back/go/go-news-kospi200-pipeline && go run ./cmd/aggregator"
start_worker "writer" "cd ~/workspace/WP_Capstone/Back/go/go-news-kospi200-pipeline && go run ./cmd/writer"
