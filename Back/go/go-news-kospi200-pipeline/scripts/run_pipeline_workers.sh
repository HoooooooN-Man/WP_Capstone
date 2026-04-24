#!/usr/bin/env bash
set -e
cd ~/workspace/WP_Capstone/Back/go/go-news-kospi200-pipeline

gnome-terminal -- bash -lc 'go run ./cmd/matcher; exec bash' 2>/dev/null || true
gnome-terminal -- bash -lc 'go run ./cmd/aggregator; exec bash' 2>/dev/null || true
gnome-terminal -- bash -lc 'go run ./cmd/writer; exec bash' 2>/dev/null || true

echo "matcher / aggregator / writer started (if gnome-terminal is available)"
echo "If not, open 3 terminals manually and run the commands."
