# WSL Runbook

## Base path
~/workspace/WP_Capstone

## Redis
Back/Redis/.env uses NetBird addresses:
- 100.67.30.5:6379
- 100.67.30.5:6380

Start Redis:
cd ~/workspace/WP_Capstone/Back/Redis
docker compose up -d

Check Redis:
docker exec -it redis-auth redis-cli -a "change_this_auth_password_123!" PING
docker exec -it redis-queue redis-cli -a "change_this_queue_password_456!" PING

## Go env
Back/go/go-news-kospi200-pipeline/configs/.env uses:
- REDIS_QUEUE_HOST=100.67.30.5
- REDIS_QUEUE_PORT=6380

## Pipeline
cd ~/workspace/WP_Capstone/Back/go/go-news-kospi200-pipeline

go run ./cmd/redis_ping
go run ./cmd/matcher
go run ./cmd/aggregator
go run ./cmd/writer
go run ./cmd/crawl_fanout
