# KOSPI200 뉴스 수집 파이프라인 설계 메모

## 1. 목표
- Google News 기반 기사 수집
- KOSPI200 종목과 매칭되는 기사만 사용
- Redis Streams에서 실시간 버퍼링/집계
- DuckDB에는 micro-batch 단위로 넘겨서 분석 부하 분리
- 크롤링 파이프라인은 redis-auth가 아닌 **redis-queue** 로 연결

## 2. 서비스 분리
### crawl_fanout / collector
- Google News RSS 검색 URL 생성
- 기사 원문 이벤트를 `news:raw` 스트림에 적재
- 운영 권장 진입점은 `crawl_fanout`

### matcher
- `news:raw`를 consumer group으로 읽음
- KOSPI200 universe alias 기준 종목 매칭
- 제목 정규화 및 dedup hash 생성
- 중복 기사 제거
- `news:normalized` 스트림에 적재

### aggregator
- `news:normalized`를 consumer group으로 읽음
- 종목별/시장별 Redis 집계 인덱스 생성
- 메모리 버퍼에 쌓았다가 일정 개수/시간마다 micro-batch 생성
- `news:batch_ready` 스트림에 적재

### writer
- `news:batch_ready`를 consumer group으로 읽음
- 기본 구현은 spool JSON 파일 생성
- DuckDB 담당자는 여기만 실제 적재 로직으로 교체

## 3. Redis 연결 정책
### 권장 서버 역할 분리
- `redis-auth: <bind_host>:6379`
  - 로그인/세션/인증 용도
- `redis-queue: <bind_host>:6380`
  - 크롤링 이벤트/스트림/배치 용도

`<bind_host>` 는 기본 `127.0.0.1`. 다중 노드/팀 공유가 필요하면 NetBird/Tailscale
사설망 IP 로 교체하되, 반드시 방화벽으로 외부 차단.

### 환경변수 우선순위
1. `REDIS_QUEUE_*`
2. `REDIS_*`
3. 미설정 시 `localhost:6379`

즉, 현재 크롤링 파이프라인은 아래처럼 두는 것을 권장한다.
```env
REDIS_QUEUE_HOST=<bind_host>
REDIS_QUEUE_PORT=6380
REDIS_QUEUE_DB=0
REDIS_QUEUE_PASSWORD=__SET_VIA_ENV__
```

## 4. Redis 키 설계
### Streams
- `news:raw`
- `news:normalized`
- `news:batch_ready`

### Consumer groups
- `matcher-group`
- `aggregator-group`
- `writer-group`

### Dedup
- `news:dedup:YYYYMMDD`
  - Redis Set
  - 값: `title_hash`
  - TTL: 72h

### Realtime index
- `news:agg:market:recent`
  - Redis Sorted Set
  - score: published_at unix
  - member: news_id
- `news:agg:company:{ticker}:recent`
  - Redis Sorted Set
- `news:item:{news_id}`
  - JSON payload string
  - TTL: 2h

## 5. 배치 정책
### 추천 기본값
- `BATCH_FLUSH_INTERVAL=1m`
- `BATCH_MAX_ITEMS=100`

### 운영 팁
- 장중 트래픽이 높으면 `BATCH_MAX_ITEMS`를 200~500으로 확대
- 프론트 digest가 더 실시간성이 필요하면 30초 flush로 줄이기
- 모델용 feature 집계는 5분 또는 장마감 기준 추가 batch 작업으로 분리

## 6. KOSPI200 universe 운영
- `data/universe/kospi200.sample.json`은 샘플 파일
- 실제 운영에서는 200개 전체 종목을 alias 포함으로 관리
- universe 갱신 담당 배치를 따로 두는 것이 좋음

## 7. DuckDB 팀 handoff 포인트
### 지금 이 레포가 넘기는 것
- 정규화된 기사 micro-batch JSON
- 문서화된 DuckDB 스키마 초안 (`docs/DUCKDB_SCHEMA.sql`)

### DuckDB 팀이 구현할 것
- spool JSON/Parquet 읽기
- `raw_news`, `news_normalized`, `news_company_map` 적재
- 일 단위 feature 계산
- digest materialization

## 8. 중복 제거 규칙
### 1차
- title normalization
- source_name
- published hour bucket

### 2차
- Redis Set `SADD`
- 동일 `title_hash`는 중복으로 간주

## 9. 감성 분석 연결 지점
현재 코드에서는 감성 분석을 비워두고 아래 위치에 연결하도록 설계됨.
- 파일: `internal/matcher/service.go`
- 함수: `normalizeAndMatch`

향후 연결 예시:
- KR-FinBERT API 호출
- Python inference service 호출
- LLM 요약/분류 서비스 호출

## 10. 운영 체크 순서
1. NetBird/VPN 연결
2. `go run ./cmd/redis_ping`
3. `go run ./cmd/matcher`
4. `go run ./cmd/aggregator`
5. `go run ./cmd/writer`
6. `go run ./cmd/crawl_fanout`
7. `spool/` 생성 확인
