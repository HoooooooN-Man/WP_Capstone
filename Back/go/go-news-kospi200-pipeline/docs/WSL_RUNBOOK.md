# WSL Runbook

## Base path
`~/workspace/WP_Capstone`

## Redis
`Back/Redis/.env` 에 호스트/포트/비밀번호 설정.
- `REDIS_BIND_HOST` (기본 `127.0.0.1`, NetBird/Tailscale 등 사설망 IP 로 교체 가능)
- `REDIS_AUTH_PORT` (기본 `6379`)
- `REDIS_QUEUE_PORT` (기본 `6380`)
- `REDIS_AUTH_PASSWORD`, `REDIS_QUEUE_PASSWORD` (각자 강력한 임의값)

Start Redis:
```bash
cd ~/workspace/WP_Capstone/Back/Redis
docker compose up -d
```

Check Redis:
```bash
docker exec -it redis-auth  redis-cli -a "$REDIS_AUTH_PASSWORD"  PING
docker exec -it redis-queue redis-cli -a "$REDIS_QUEUE_PASSWORD" PING
```

## Go env
`Back/go/go-news-kospi200-pipeline/configs/.env` 에 다음 설정:
- `REDIS_QUEUE_HOST=<bind_host>`  (예: `127.0.0.1` 또는 사설망 IP)
- `REDIS_QUEUE_PORT=6380`

## Pipeline
```bash
cd ~/workspace/WP_Capstone/Back/go/go-news-kospi200-pipeline

go run ./cmd/redis_ping
go run ./cmd/matcher
go run ./cmd/aggregator
go run ./cmd/writer
go run ./cmd/crawl_fanout
```
