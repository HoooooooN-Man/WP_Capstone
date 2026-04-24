#!/usr/bin/env bash
set -euo pipefail

cd ~/workspace/WP_Capstone/Back/go/go-news-kospi200-pipeline
mkdir -p logs

source .venv/bin/activate
python scripts/build_query_plan.py > logs/build_query_plan.log 2>&1

go run ./cmd/crawl_fanout > logs/crawl_fanout.log 2>&1