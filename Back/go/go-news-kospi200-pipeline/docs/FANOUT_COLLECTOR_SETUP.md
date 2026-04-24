# Fan-out Collector Setup

## Added files
- `cmd/crawl_fanout/main.go`
- `cmd/redis_ping/main.go`
- `internal/planner/query_plan.go`
- `scripts/run_crawl_fanout.bat`
- `scripts/run_redis_ping.bat`

## What it does
- Reads `data/plans/current/query-plan.current.json`
- Executes query jobs concurrently with a worker pool
- Fetches Google News RSS results for each job query
- Pushes raw items into Redis `news:raw`
- Assumes crawling pipeline should connect to **redis-queue**

## Environment variables
### Redis queue priority
- `REDIS_QUEUE_ADDR`
- `REDIS_QUEUE_HOST`
- `REDIS_QUEUE_PORT`
- `REDIS_QUEUE_PASSWORD`
- `REDIS_QUEUE_DB`
- `REDIS_QUEUE_PROTOCOL`

If these are missing, code falls back to generic `REDIS_*` variables.

### Runtime
- `QUERY_PLAN_PATH` (default: `data/plans/current/query-plan.current.json`)
- `CRAWL_WORKERS` (default: `6`)
- `CRAWL_JOB_DELAY` (default: `250ms`)
- `CRAWL_FETCH_TIMEOUT` (default: request timeout from config)
- `CRAWL_MAX_JOBS` (default: `0`, meaning all jobs)
- `APP_ENV_FILE` (optional, preferred: `configs/.env`)

## Recommended `.env`
```env
REDIS_QUEUE_HOST=100.67.30.5
REDIS_QUEUE_PORT=6380
REDIS_QUEUE_DB=0
REDIS_QUEUE_PASSWORD=
```

## Connectivity check
```powershell
cd D:\Workspace\WP_Capstone\Back\go\go-news-kospi200-pipeline
$env:APP_ENV_FILE="configs/.env"
go run ./cmd/redis_ping
```

## Manual run
```powershell
cd D:\Workspace\WP_Capstone\Back\go\go-news-kospi200-pipeline
$env:APP_ENV_FILE="configs/.env"
$env:QUERY_PLAN_PATH="data/plans/current/query-plan.current.json"
$env:CRAWL_WORKERS="6"
$env:CRAWL_JOB_DELAY="300ms"
$env:CRAWL_FETCH_TIMEOUT="12s"
go run ./cmd/crawl_fanout
```

## Limited smoke test
```powershell
cd D:\Workspace\WP_Capstone\Back\go\go-news-kospi200-pipeline
$env:APP_ENV_FILE="configs/.env"
$env:CRAWL_MAX_JOBS="10"
go run ./cmd/crawl_fanout
```

## Typical pipeline order
1. NetBird/VPN 연결
2. `go run ./cmd/redis_ping`
3. Run `daily_universe_updater.py`
4. Run `build_query_plan.py`
5. Start `matcher` / `aggregator` / `writer`
6. Run `crawl_fanout`
7. Check `spool/` output

## Windows Scheduler recommendation
- Scheduler action: `scripts/run_crawl_fanout.bat`
- Start in: `D:\Workspace\WP_Capstone\Back\go\go-news-kospi200-pipeline`
- First validate `scripts/run_redis_ping.bat`
- If scheduler fails but manual run works, check `.env` path and Start in directory first
