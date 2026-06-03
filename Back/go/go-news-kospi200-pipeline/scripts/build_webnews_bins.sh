#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p bin

go build -o bin/webnews_collector ./cmd/webnews_collector
go build -o bin/webnews_enricher ./cmd/webnews_enricher
go build -o bin/webnews_scheduler ./cmd/webnews_scheduler
go build -o bin/webnews_finalizer ./cmd/webnews_finalizer
go build -o bin/webnews_publish ./cmd/webnews_publish
go build -o bin/webnews_prune ./cmd/webnews_prune
go build -o bin/webnews_body_fetcher ./cmd/webnews_body_fetcher

echo "[OK] build complete"
ls -lh bin/webnews_*
go build -o bin/webnews_url_resolver ./cmd/webnews_url_resolver
go build -o bin/webnews_summary ./cmd/webnews_summary
go build -o bin/webnews_summary_publish ./cmd/webnews_summary_publish
