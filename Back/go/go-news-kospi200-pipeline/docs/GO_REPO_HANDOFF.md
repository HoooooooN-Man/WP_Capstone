# Go 뉴스 파이프라인 레포 handoff 정리

이 문서는 Go 담당자가 현재 작업분을 Git 레포에 push할 때 함께 올리기 위한 요약 문서다.

## 이번 커밋의 범위
- Google News RSS 수집기 뼈대 추가
- KOSPI200 종목 alias 매칭기 뼈대 추가
- Redis Streams 기반 파이프라인 뼈대 추가
- Redis 집계/배치 생성기 추가
- DuckDB 담당자 전달용 writer 인터페이스 및 스키마 문서 추가

## 핵심 아키텍처
```text
collector -> news:raw -> matcher -> news:normalized -> aggregator -> news:batch_ready -> writer
```

## 서비스 설명
### collector
- Google News RSS 검색 결과를 가져와 raw 이벤트 생성
- Redis Stream `news:raw`에 적재

### matcher
- KOSPI200 universe alias 기준으로 기사와 종목 매칭
- 제목 정규화 및 dedup hash 생성
- 중복 제거 후 `news:normalized`에 적재

### aggregator
- 정규화 기사 이벤트를 읽어 종목별/시장별 Redis 인덱스 생성
- micro-batch를 만들어 `news:batch_ready`에 적재

### writer
- batch를 받아 현재는 spool JSON으로 저장
- 추후 DuckDB 직접 적재 구현으로 교체 예정

## 현재 샘플/가짜 데이터
- `data/universe/kospi200.sample.json`은 샘플 5개 종목만 있음
- 실제 push 전에 200개 종목 alias 파일로 교체 권장

## 운영 전에 꼭 해야 할 일
1. 실제 KOSPI200 종목 200개 alias 파일 작성
2. Google News 검색어 세트 확정
3. KR-FinBERT 또는 감성분석 서비스 연결
4. DuckDB writer 구현
5. Redis 운영 파라미터 점검

## DuckDB 담당자에게 전달할 파일
- `docs/DUCKDB_SCHEMA.sql`
- `internal/writer/duckdb_stub.go`
- `docs/REDIS_DUCKDB_PIPELINE.md`

## 권장 커밋 메시지 예시
```text
Add Go skeleton for KOSPI200 news pipeline with Redis Streams and DuckDB handoff docs
```


## universe/alias 운영 추가사항
- current / archive / archive-monthly 체계를 추가했다.
- 운영 current 파일은 `data/universe/current/` 아래 3종이다.
- 최근 30일 일별 보관 + 월별 장기 스냅샷 정책은 `docs/UNIVERSE_RETENTION_POLICY.md` 참고.
- `go run ./cmd/universe_maintainer -as-of-date YYYY-MM-DD` 로 스냅샷/정리를 수행할 수 있다.
