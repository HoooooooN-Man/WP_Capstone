# go-news-kospi200-pipeline

Google News RSS 기반 KOSPI200 뉴스 수집 파이프라인의 Go 뼈대 프로젝트.

## 포함 범위
- collector / matcher / aggregator / writer 서비스 분리
- Redis Streams 기반 파이프라인
- KOSPI200 alias 매칭
- micro-batch handoff 구조
- DuckDB 팀 전달용 스키마 문서 포함
- current / daily archive / monthly snapshot 기반 universe 보관 정책

## 디렉터리 구조
```text
cmd/
  collector/
  matcher/
  aggregator/
  writer/
  universe_maintainer/
internal/
  aggregator/
  config/
  matcher/
  model/
  redisx/
  rss/
  util/
  writer/
configs/
  .env.example
data/
  universe/
    current/
    archive/
    archive-monthly/
docs/
  DUCKDB_SCHEMA.sql
  REDIS_DUCKDB_PIPELINE.md
  KOSPI200_ALIAS_RULES.md
  UNIVERSE_RETENTION_POLICY.md
```

## 빠른 시작
### 1) 의존성 설치
```bash
go mod tidy
```

### 2) 환경변수 준비
현재 코드는 `.env` 자동 로더를 붙이지 않았으므로, 첫 실행은 기본값으로 진행하거나 환경변수를 직접 주입한다.
기본 universe 경로는 `data/universe/current/kospi200.aliases.current.json` 이다.

### 3) Redis 실행 확인
로컬 Redis가 `localhost:6379`에서 떠 있다고 가정.

### 4) 서비스 실행
```bash
go run ./cmd/matcher
go run ./cmd/aggregator
go run ./cmd/writer
go run ./cmd/collector
```

## 서비스 흐름
```text
collector -> news:raw -> matcher -> news:normalized -> aggregator -> news:batch_ready -> writer
```

## 현재 writer 기본 동작
현재 writer는 DuckDB에 직접 쓰지 않고 `./spool` 아래에 batch JSON 파일을 생성한다.
이 부분은 DuckDB 담당자가 `internal/writer/duckdb_stub.go`를 실제 구현으로 교체하면 된다.

## KOSPI200 universe/alias 운영
운영용 current 파일 3종:
- `data/universe/current/kospi200.constituents.current.json`
- `data/universe/current/kospi200.aliases.current.json`
- `data/universe/current/kospi200.match_rules.current.json`

보관 정책:
- `archive/`: 최근 30일 일별 보관
- `archive-monthly/`: 월별 장기 스냅샷

스냅샷 명령:
```bash
go run ./cmd/universe_maintainer -as-of-date 2026-03-29
```

## 꼭 바꿔야 하는 것
- `data/universe/current/kospi200.aliases.current.json` -> 실제 KOSPI200 200종목 alias 파일로 교체
- `data/universe/current/kospi200.constituents.current.json` -> 실제 KOSPI200 200종목 구성종목으로 교체
- `NEWS_QUERIES` -> 운영용 검색어 세트
- 감성 분석 연결
- 기사 원문 URL 해석 로직

## 문서
- `docs/REDIS_DUCKDB_PIPELINE.md`: Redis/DuckDB 아키텍처 요약
- `docs/DUCKDB_SCHEMA.sql`: DuckDB 팀 전달용 스키마 초안
- `docs/KOSPI200_ALIAS_RULES.md`: alias 생성/운영 규칙
- `docs/UNIVERSE_RETENTION_POLICY.md`: 30일 일별 + 월별 스냅샷 정책
