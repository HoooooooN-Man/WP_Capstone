#!/usr/bin/env bash
set -e
cd ~/workspace/WP_Capstone/Back/go/go-news-kospi200-pipeline
source .venv/bin/activate
python scripts/daily_universe_updater.py
