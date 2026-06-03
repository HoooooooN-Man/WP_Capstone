# KOSPI200 / ML News Pipeline Legacy

이 디렉터리는 기존 KOSPI200 기반 ML 입력용 뉴스 크롤링 파이프라인을 보관하기 위한 legacy 영역이다.

현재 운영 대상은 `Webnews RSS-only daily batch` 구조이며, 이 legacy 코드는 Oracle Cloud 운영 배치에 포함하지 않는다.

## 기존 역할

- KOSPI200 universe 관리
- query plan 생성
- Google News RSS 기반 종목별 뉴스 수집
- matcher / aggregator / writer 처리
- Redis Streams 기반 중간 처리
- spool 파일 생성
- DuckDB handoff
- coverage report 생성

## 현재 운영 구조에서 제외하는 이유

- Webnews는 서비스 화면 표시용 뉴스 current JSON 생성이 목적이다.
- ML 입력용 대량 뉴스 적재는 현재 운영 우선순위에서 제외되었다.
- Oracle Cloud Always Free VM 운영을 위해 상시 worker와 대량 누적 구조를 제거한다.
- Redis와 파일 시스템의 보관량을 최소화한다.

## 주의

이 디렉터리는 Go 빌드 대상에서 제외하기 위해 `_legacy` 하위에 둔다.
운영 배치에서는 참조하지 않는다.