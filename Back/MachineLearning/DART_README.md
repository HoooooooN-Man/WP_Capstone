# DART Open API 통합 — 라이선스·API 한도 박제

> 차차기 W5 Step 1. CLAUDE.md §반드시 지킬 것 3: "DART 데이터 통합 시 라이선스·API 한도 README 박제."

## 라이선스

- **공급자**: 금융감독원 (FSS) DART (전자공시시스템)
- **API**: Open API — https://opendart.fss.or.kr/
- **이용약관**: https://opendart.fss.or.kr/intro/main.do
- **저작권**: 금융감독원. 본 시스템에서 *수집·가공된 데이터* 는 *공시 유형 코드* 와
  *접수번호·접수일자* 위주로 저장. **본문 텍스트·재무 수치 raw 저장 안 함.**
- **재배포 제한**: DART 약관에 따라 *원본 그대로 배포 금지*. 본 시스템은 내부 추천 신호 피처화
  목적으로만 사용. 외부 API 응답으로 *원본 공시 텍스트 노출 금지*.

## API 한도

- **인증**: 무료 API key (이메일 발급)
- **호출 한도**: **일 10,000회** (변동 가능, 공식 페이지 확인)
- **본 시스템 보호 정책**:
  - `dart_client.DEFAULT_RATE_LIMIT_SEC = 0.2` → 5 req/s (이론 최대 432,000/일,
    한도 5% 미만 사용)
  - 일별 쪼개 호출 (`dart_ingest.py` 의 `_daterange`) — 한 번에 큰 기간 부담 회피
  - 429·5xx 자동 재시도 (max 3회, 지수 backoff)
- **권장 사용 패턴**:
  - 초기 백필: 일 단위 loop, listed-only 필터, 한 번에 1주 ≤
  - 일상 운영: cron 으로 *전날 공시* 만 ingest

## 수집 범위 (차차기 §절대 5 준수)

> "DART API 통합 시 raw 텍스트 파싱 의존도 높이지 말 것. 공시 *유형 코드* 위주, 텍스트는 보조."

`disclosures` DuckDB 테이블 schema:

| 컬럼 | 의미 |
|---|---|
| `rcept_no` | 접수번호 (PK) |
| `corp_code` | DART 8자리 회사 코드 |
| `corp_name` | 회사명 |
| `stock_code` | KRX 6자리 (상장 종목만 채워짐) |
| `rcept_dt` | 접수일자 (YYYYMMDD) |
| `report_nm` | 공시명 (제목, 인덱싱·필터용 — 텍스트 *분석* 안 함) |
| `pblntf_ty` | 1차 유형 (A~J, `dart_client.PBLNTF_TY_CODES`) |
| `pblntf_detail_ty` | 2차 유형 |
| `flr_nm` | 제출인 |
| `rm` | 비고 |

**저장 안 함:**
- 공시 본문 (XBRL·HTML·PDF 원문)
- 재무제표 raw 수치 (DART `/api/fnlttSinglAcnt.json` 등 — 차차차기 검토)
- 첨부파일 (`/api/document.xml`)

## 인증·환경변수

```bash
# 사용자 발급 후 환경변수에 (.env 또는 shell rc)
export DART_API_KEY="<발급받은 40자 hex>"
```

`Back/FastAPI/.env.example` 에는 키 노출 금지. 실 키는 `.env` (gitignore 됨).

## 사용 예

```bash
# 1일치 ingest (테스트용)
py Back/MachineLearning/dart_ingest.py --start 2026-04-29 --end 2026-04-29 --listed-only

# 1주 ingest (주요사항보고만)
py Back/MachineLearning/dart_ingest.py --start 2026-04-23 --end 2026-04-29 \
    --pblntf-ty B --listed-only

# Dry-run (실 적재 생략)
py Back/MachineLearning/dart_ingest.py --start 2026-04-29 --end 2026-04-29 --dry-run
```

## 차차차기 후보 (W5 컷 — 추천 흐름 통합)

차차기_사이클.md §컷 우선순위 2 명시: "W5 DART → 데이터 수집·피처화만, 추천 흐름 통합은
차차차기."

차차차기 진입 시 후보:
- `disclosures` → ticker × date binary/count features 피처화 (예: "지난 5일 주요사항 보고
  발생 여부", "지분공시 카운트")
- 어닝 (정기공시 A) D-day 계산 → coverage·diversify 와 결합
- v12 학습 input 에 dart features 합류 (W5 ablation 수준)
- 재무 raw 통합 (`fnlttSinglAcnt.json`) 검토 — 단 약관·라이선스 재확인
