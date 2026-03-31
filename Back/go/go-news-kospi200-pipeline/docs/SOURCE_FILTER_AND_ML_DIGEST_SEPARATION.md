# Source Filter + ML/Digest Separation

## Added
- `data/policies/news_source_policy.current.json`
- `internal/matcher/source_policy.go`

## Changed
- `cmd/matcher/main.go`
- `internal/config/config.go`
- `internal/matcher/service.go`
- `internal/matcher/universe.go`
- `internal/model/news.go`
- `scripts/daily_coverage_report.py`

## Goal
- Keep broad digest coverage.
- Exclude low-quality / aggregator / repetitive stock-note sources from ML.
- Preserve macro queries as digest-only.

## Default ML-blocked sources
- 네이트
- v.daum.net
- 다음
- 톱스타뉴스 / topstarnews.net
- 주달

## Default ML-blocked title patterns
- 투자분석
- 장중
- 주가,
- 오늘의 증시일정
- [오늘의 증시일정]
- 증시일정
