# KOSPI200 alias 생성/운영 규칙

## 목적
이 문서는 `data/universe/current/kospi200.aliases.current.json` 생성 기준을 정리한다.
이 파일은 단순 종목 목록이 아니라, 뉴스 기사 제목/스니펫을 KOSPI200 종목에 매칭하기 위한 별칭 사전이다.

## source of truth
- KRX Data Marketplace > 지수구성종목
- KRX Data Marketplace > 주가지수 공지

## 파일 역할 분리
- `kospi200.constituents.current.json`: 현재 공식 KOSPI200 구성종목 목록
- `kospi200.aliases.current.json`: 기사 매칭용 alias/negative_aliases/search_queries
- `kospi200.match_rules.current.json`: 전역 규칙/금지어/약한 alias 기준

## alias 생성 기본 규칙
반드시 포함:
1. 공식 한글 종목명
2. 대표 영문명 또는 기사에서 자주 쓰는 영문 표기
3. 6자리 종목코드

조건부 포함:
1. 실제 기사에서 반복 등장하는 안정적인 약칭
2. 회사명과 결합된 사업/이슈 키워드 (예: `삼성전자 반도체`)

넣지 말아야 할 것:
1. 그룹명 단독 (`삼성`, `SK`, `LG`, `현대`, `한화`, `두산`)
2. 너무 짧은 영문 토큰 (`SK`, `GS`, `CJ`)
3. 다른 종목과 충돌하는 불명확 약칭

## negative_aliases 사용 규칙
`negative_aliases`는 기사 매칭 오탐을 방지하기 위한 금지 토큰이다.
예시:
- `SK하이닉스`의 `negative_aliases`: `SK`
- `현대차`의 `negative_aliases`: `현대`

## search_queries 사용 규칙
`search_queries`는 collector 검색어 후보이며, `aliases`보다 조금 넓게 잡을 수 있다.
검색은 넓게, 매칭은 보수적으로 운영한다.

## 운영 절차
1. KRX에서 현재 KOSPI200 구성종목을 수집한다.
2. `constituents` 파일을 갱신한다.
3. 자동 규칙으로 `aliases` 초안을 만든다.
4. 오탐 위험 종목을 수동 보정한다.
5. matcher dry-run 후 오탐/누락을 수정한다.
6. `cmd/universe_maintainer`로 스냅샷을 남긴다.

## 보관 규칙
- current: 최신 1세트 유지
- daily archive: 최근 30일 보관
- monthly snapshot: 월 1회 장기 보관
