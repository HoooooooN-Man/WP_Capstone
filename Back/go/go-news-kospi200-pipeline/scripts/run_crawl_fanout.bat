@echo off
cd /d D:\Workspace\WP_Capstone\Back\go\go-news-kospi200-pipeline
set APP_ENV_FILE=configs\.env
set QUERY_PLAN_PATH=data\plans\current\query-plan.current.json
set CRAWL_WORKERS=6
set CRAWL_JOB_DELAY=300ms
set CRAWL_FETCH_TIMEOUT=12s

echo [1/2] Redis queue connectivity check...
go run .\cmd\redis_ping || goto :error

echo [2/2] Crawl fan-out start...
go run .\cmd\crawl_fanout || goto :error

goto :eof

:error
echo Script failed with error level %errorlevel%
exit /b %errorlevel%
