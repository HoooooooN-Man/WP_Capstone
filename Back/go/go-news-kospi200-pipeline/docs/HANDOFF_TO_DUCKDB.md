# HANDOFF_TO_DUCKDB

## 1. 목적

이 파이프라인은 Redis Streams에서 뉴스 수집/정규화/집계를 수행한 뒤,
DuckDB 적재 담당 프로세스가 바로 읽을 수 있도록 batch JSON 파일을 spool 디렉터리에 생성한다.

이 문서는 Go crawling pipeline과 DuckDB 적재 담당자 사이의 handoff 규격을 정의한다.

---

## 2. 현재 흐름

```text
crawl_fanout(or collector)
  -> news:raw
matcher
  -> news:normalized
aggregator
  -> news:batch_ready
writer
  -> spool/pending/{batch_id}.json