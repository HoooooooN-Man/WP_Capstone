# Universe/Alias 보관 정책

## 목표
- 운영용 최신 KOSPI200 universe/alias를 유지한다.
- 최근 변경 이력을 30일간 보존한다.
- 프로젝트 추적성과 백테스트를 위해 월별 장기 스냅샷을 남긴다.

## 디렉터리
```text
data/
  universe/
    current/
      kospi200.constituents.current.json
      kospi200.aliases.current.json
      kospi200.match_rules.current.json
    archive/
      YYYY-MM-DD/
        kospi200.constituents.YYYY-MM-DD.json
        kospi200.aliases.YYYY-MM-DD.json
        kospi200.match_rules.YYYY-MM-DD.json
    archive-monthly/
      YYYY-MM/
        kospi200.constituents.YYYY-MM-DD.json
        kospi200.aliases.YYYY-MM-DD.json
        kospi200.match_rules.YYYY-MM-DD.json
```

## 보관 원칙
- `current/`: 서비스가 읽는 최신 파일
- `archive/`: 최근 30일 일별 스냅샷
- `archive-monthly/`: 월별 장기 스냅샷

## 삭제 규칙
- `archive/` 아래 일별 디렉터리는 기본적으로 최근 30일만 유지한다.
- 월말 스냅샷은 `archive-monthly/`에 별도로 복사한다.
- `archive-monthly/`는 프로젝트 종료 시점까지 보관하거나, 최소 12개월 이상 보관을 권장한다.

## 운영 루틴
1. KRX 지수구성종목/주가지수 공지를 확인한다.
2. current 파일 3개를 갱신한다.
3. `go run ./cmd/universe_maintainer -as-of-date YYYY-MM-DD` 를 실행한다.
4. 신규 일별 스냅샷이 생성되는지 확인한다.
5. 30일 초과 일별 폴더가 정리되는지 확인한다.
6. 월말이면 `archive-monthly/YYYY-MM/` 경로도 생성되는지 확인한다.

## 백테스트 관점
- 일별 30일 보관은 최근 운영 이슈와 alias 변경 원인을 추적하는 데 유리하다.
- 월별 장기 스냅샷은 백테스트/재현성/회고 보고서 작성에 유리하다.
