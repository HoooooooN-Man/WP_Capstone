# Go 파이프라인 — 구조화 로그 + Loki/Grafana

## 1. 로그 형식

각 cmd (`collector`, `matcher`, `aggregator`, `writer`, `crawl_fanout`) 는
표준 라이브러리 `log/slog` 로 구조화 JSON 로그를 stderr 에 출력한다.

```json
{
  "time": "2026-05-05T15:00:01.123Z",
  "level": "INFO",
  "msg": "query processed",
  "service": "collector",
  "env": "prod",
  "query": "삼성전자",
  "fetched": 23,
  "pushed": 23
}
```

### 환경변수
| 변수 | 기본 | 설명 |
|------|------|------|
| `LOG_LEVEL`  | `info` | `debug` / `info` / `warn` / `error` |
| `LOG_FORMAT` | `json` | `json` 또는 `text` (개발 시 가독성용) |
| `APP_ENV`    | `dev`  | `service` 와 함께 모든 라인에 부착됨 |

## 2. 로컬에서 보기 좋게 출력

```bash
# pretty-print
go run ./cmd/matcher 2>&1 | jq .

# tail + filter
go run ./cmd/writer 2>&1 | jq 'select(.level=="ERROR")'
```

## 3. Loki 로 적재 (Promtail)

`Back/go/go-news-kospi200-pipeline/deploy/promtail-config.yaml` 예시:

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: go-news-pipeline
    static_configs:
      - targets: [localhost]
        labels:
          app: go-news-pipeline
          __path__: /var/log/go-news-pipeline/*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            service: service
            msg: msg
            env: env
      - labels:
          level:
          service:
          env:
      - timestamp:
          source: time
          format: RFC3339Nano
```

각 cmd 를 실행할 때 stderr 를 파일로 리다이렉트:

```bash
go run ./cmd/matcher 2>> /var/log/go-news-pipeline/matcher.log
```

또는 systemd unit 파일에서 `StandardError=append:/var/log/go-news-pipeline/...` 사용.

## 4. Loki + Grafana docker-compose 예시

`deploy/observability.docker-compose.yml`:

```yaml
services:
  loki:
    image: grafana/loki:3.2.1
    ports: ["3100:3100"]
    command: -config.file=/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:3.2.1
    volumes:
      - ./promtail-config.yaml:/etc/promtail/config.yaml
      - /var/log/go-news-pipeline:/var/log/go-news-pipeline:ro
    command: -config.file=/etc/promtail/config.yaml

  grafana:
    image: grafana/grafana:11.4.0
    ports: ["3000:3000"]
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=__set_via_env__
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  grafana-data:
```

## 5. 추천 Grafana 패널 (LogQL 쿼리)

### 에러 빈도 (서비스별)
```logql
sum by (service) (
  count_over_time({app="go-news-pipeline", level="ERROR"}[5m])
)
```

### Collector 처리량
```logql
sum by (query) (
  rate({app="go-news-pipeline", service="collector"} |~ "query processed" [1m])
)
```

### Writer 적재 지연
```logql
{app="go-news-pipeline", service="writer"}
| json
| msg = "batch flushed"
| unwrap latency_ms
```

## 6. 운영 체크리스트

1. `LOG_FORMAT=json LOG_LEVEL=info` 로 모든 cmd 기동.
2. 로그 디렉토리는 `logrotate` 로 일별 회전 (이미 .gitignore 처리됨).
3. Promtail 이 `/var/log/go-news-pipeline/*.log` 를 tail.
4. Grafana 에 Loki datasource 등록 (`http://loki:3100`).
5. 위 패널들을 대시보드에 import.
6. 알림 (Grafana Alerting): 5분간 ERROR 가 10건 이상이면 Slack/Discord 웹훅.
