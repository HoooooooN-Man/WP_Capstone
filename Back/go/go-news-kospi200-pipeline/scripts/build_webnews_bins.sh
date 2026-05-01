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

echo "[OK] build complete"
ls -lh bin/webnews_*