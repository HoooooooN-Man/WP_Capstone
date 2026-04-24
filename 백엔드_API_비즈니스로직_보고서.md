# 백엔드 API 및 주요 비즈니스 로직 보고서

> **프로젝트**: WP_Capstone — 주식 추천 시스템  
> **작성일**: 2026-04-13  
> **대상 경로**: `Back/`

---

## 목차

1. [시스템 아키텍처 개요](#1-시스템-아키텍처-개요)
2. [데이터베이스 구조](#2-데이터베이스-구조)
3. [FastAPI 추천 서버 (포트 8001)](#3-fastapi-추천-서버-포트-8001)
   - 3.1 [앱 초기화 및 설정](#31-앱-초기화-및-설정)
   - 3.2 [종목 추천 API — `/api/v1/stocks`](#32-종목-추천-api--apiv1stocks)
   - 3.3 [포트폴리오 API — `/api/v1/portfolio`](#33-포트폴리오-api--apiv1portfolio)
   - 3.4 [차트 API — `/api/v1/chart`](#34-차트-api--apiv1chart)
   - 3.5 [재무 API — `/api/v1/finance`](#35-재무-api--apiv1finance)
   - 3.6 [스크리너 API — `/api/v1/screener`](#36-스크리너-api--apiv1screener)
   - 3.7 [종목 비교 API — `/api/v1/compare`](#37-종목-비교-api--apiv1compare)
   - 3.8 [마켓 레이더 API — `/api/v1/market`](#38-마켓-레이더-api--apiv1market)
   - 3.9 [커뮤니티 게시판 API — `/api/v1/board`](#39-커뮤니티-게시판-api--apiv1board)
4. [인증/사용자 서버 (포트 8000)](#4-인증사용자-서버-포트-8000)
5. [서비스 레이어 — `services/data.py`](#5-서비스-레이어--servicesdata-py)
6. [머신러닝 전처리 파이프라인](#6-머신러닝-전처리-파이프라인)
   - 6.1 [ML 점수 적재 — `precompute_scores.py`](#61-ml-점수-적재--precompute_scorespy)
   - 6.2 [재무 스코어 적재 — `precompute_finance.py`](#62-재무-스코어-적재--precompute_financepy)
   - 6.3 [가격·이동평균 적재 — `precompute_chart.py`](#63-가격이동평균-적재--precompute_chartpy)
7. [데이터 모델 및 스키마](#7-데이터-모델-및-스키마)
8. [캐싱 전략](#8-캐싱-전략)
9. [주요 비즈니스 로직 요약](#9-주요-비즈니스-로직-요약)

---

## 1. 시스템 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                      │
│                      http://localhost:5174                   │
└────────────────┬──────────────────┬─────────────────────────┘
                 │                  │
                 ▼                  ▼
┌───────────────────────┐  ┌──────────────────────┐
│  FastAPI 추천 서버     │  │  FastAPI 인증 서버    │
│   포트 8001            │  │   포트 8000           │
│   Back/FastAPI/        │  │   Back/db/            │
└──────────┬────────────┘  └────────────┬─────────┘
           │                            │
     ┌─────▼──────┐               ┌─────▼──────┐
     │  DuckDB    │               │ PostgreSQL  │
     │scores.duckdb│              │  (사용자DB) │
     │ - scores   │               └────────────┘
     │ - finance  │               ┌────────────┐
     │ - prices   │               │   Redis    │
     └─────┬──────┘               │(세션/인증) │
           │                      └────────────┘
     ┌─────▼──────┐
     │   Redis    │
     │(API 캐시)  │
     └────────────┘
     ┌─────────────┐
     │   SQLite    │
     │ board.db    │
     │(커뮤니티)   │
     └─────────────┘
```

**서버 구성 요약**

| 서버 | 포트 | 역할 | DB |
|------|------|------|----|
| `FastAPI/main.py` | 8001 | ML 추천·분석·게시판 | DuckDB + SQLite + Redis(캐시) |
| `db/server.py` | 8000 | 회원 인증·뉴스 인제스트 | PostgreSQL + Redis(세션) |

---

## 2. 데이터베이스 구조

### 2.1 DuckDB (`scores.duckdb`) — OLAP

세 개의 테이블이 단일 파일에 공존한다.

#### `scores` 테이블 — ML 추천 점수

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `date` | DATE | 예측 기준일 |
| `ticker` | VARCHAR | 종목코드 (6자리 zero-pad) |
| `name` | VARCHAR | 종목명 |
| `sector` | VARCHAR | WICS 대분류 섹터 |
| `mid_sector` | VARCHAR | WICS 중분류 섹터 |
| `close` | FLOAT | 종가 |
| `prob_lgbm` | FLOAT | LightGBM 예측 확률 (0~1) |
| `prob_xgb` | FLOAT | XGBoost 예측 확률 (0~1) |
| `prob_cat` | FLOAT | CatBoost 예측 확률 (0~1) |
| `prob_ensemble` | FLOAT | 앙상블 확률 = (lgbm+xgb+cat)/3 |
| `score` | FLOAT | 백분위 점수 (1~100) |
| `rank_in_date` | INTEGER | 해당 날짜 내 순위 (1=최상위) |
| `total_in_date` | INTEGER | 해당 날짜 전체 종목 수 |
| `tier` | VARCHAR | 등급 A/B/C/D |
| `model_version` | VARCHAR | 모델 버전 태그 (예: v7, v8) |
| `inserted_at` | VARCHAR | DuckDB 적재 시각 |

#### `finance` 테이블 — 분기별 재무 지표

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `ticker` | VARCHAR | 종목코드 |
| `name` | VARCHAR | 회사명 |
| `year` / `quarter` | INTEGER | 연도·분기 (PK 구성) |
| `base_date` | VARCHAR | 기준일 (YYYY-MM-DD) |
| `market_cap` | DOUBLE | 시가총액 |
| `per` / `pbr` / `eps` / `bps` / `dps` | DOUBLE | 가치 지표 |
| `dividend_yield` | DOUBLE | 배당수익률 (%) |
| `op_margin` / `net_margin` | DOUBLE | 영업·순이익률 (%) |
| `roe` | DOUBLE | 자기자본이익률 (%) |
| `debt_ratio` | DOUBLE | 부채비율 (%) |
| `current_ratio` | DOUBLE | 유동비율 (%) |
| `revenue` / `op_profit` / `net_profit` | DOUBLE | 손익 지표 |
| `equity` / `total_debt` / `current_assets` / `current_liab` | DOUBLE | 재무상태표 |
| `rev_growth_yoy` / `rev_growth_qoq` | DOUBLE | 매출 성장률 (%) |
| `op_growth_yoy` / `op_growth_qoq` | DOUBLE | 영업이익 성장률 (%) |
| `finance_score` | DOUBLE | 재무 종합 점수 (0~100) |

#### `prices` 테이블 — 일별 OHLCV + 이동평균

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `ticker` | VARCHAR | 종목코드 |
| `date` | VARCHAR | 날짜 (YYYY-MM-DD, PK 구성) |
| `open` / `high` / `low` / `close` | DOUBLE | 시가·고가·저가·종가 |
| `volume` / `amount` | DOUBLE | 거래량·거래대금 |
| `market_cap` | DOUBLE | 시가총액 |
| `ma5` / `ma20` / `ma60` / `ma120` | DOUBLE | 이동평균선 |

### 2.2 PostgreSQL — 사용자 DB

```
users
  user_id (PK)  email (UNIQUE)  hashed_password  nickname (UNIQUE)
  is_active     is_verified     created_at

user_watchlist
  id (PK)  user_id (FK→users)  ticker

notifications
  id (PK)  user_id (FK→users)  ticker  title
  sentiment_label (FinBERT 결과)  is_read  created_at
```

### 2.3 SQLite (`board.db`) — 커뮤니티 게시판

```
posts
  id (PK)  ticker  author_id  title  content  views  likes  created_at

comments
  id (PK)  post_id (FK→posts CASCADE)  author_id  content  created_at

post_likes
  post_id + author_id (PK 복합)  ← 중복 좋아요 DB 레벨 차단
```

### 2.4 Redis

| 서버 | DB | 용도 | TTL |
|------|-----|------|-----|
| 추천 서버 (db=1) | `ml_api:*` | API 응답 캐시 | 60~600초 |
| 인증 서버 (db=0) | `verify:{email}` | 이메일 인증 코드 | 180초 |
| 인증 서버 (db=0) | `confirmed:{email}` | 인증 완료 플래그 | 300초 |
| 인증 서버 (db=0) | `session:{token}` | 로그인 세션 | 3600초 |

---

## 3. FastAPI 추천 서버 (포트 8001)

### 3.1 앱 초기화 및 설정

**`FastAPI/core/config.py`** — 모든 경로·환경 상수 중앙 관리

```
CAPSTONE_ROOT  = 프로젝트 루트 (Capstone Data/)
MODELS_DIR     = CAPSTONE_ROOT/models
SEED_CSV       = CAPSTONE_ROOT/preprocessing/seed.csv
DUCKDB_PATH    = Back/FastAPI/scores.duckdb
BOARD_DB_PATH  = Back/FastAPI/board.db
REDIS_HOST/PORT/DB = localhost:6379 db=1
REDIS_CACHE_TTL = 60초
API_PREFIX     = /api/v1
APP_VERSION    = 1.0.0
```

**`FastAPI/main.py`** — lifespan 이벤트

1. SQLite 게시판 DB 자동 초기화 (`init_board_db`)
2. DuckDB 파일 존재 여부 확인
3. 비동기 executor로 DuckDB 연결 + `scores / finance / prices` 테이블 각 500행 워밍업 (OS 파일 캐시 확보, 첫 요청 지연 제거)

**헬스체크 엔드포인트**

| Method | Path | 응답 |
|--------|------|------|
| GET | `/` | `{status, app, version, docs}` |
| GET | `/health` | `{status, duckdb_exists, duckdb_path}` |

---

### 3.2 종목 추천 API — `/api/v1/stocks`

#### GET `/api/v1/stocks/versions`

모델 버전 목록 조회

- **로직**: `scores` 테이블에서 `DISTINCT model_version` 조회, `inserted_at` 오름차순 정렬
- **응답**: `VersionsResponse { versions: ["v7","v8"], latest: "v8" }`
- **캐시**: 300초

---

#### GET `/api/v1/stocks/dates`

사용 가능한 날짜 목록 조회

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `model_version` | string | `latest` | 모델 버전 |

- **로직**: `SELECT DISTINCT CAST(date AS VARCHAR) ... ORDER BY 1`
- **응답**: `DatesResponse { model_version, dates: [...], latest }`
- **에러**: DuckDB 비어있으면 503

---

#### GET `/api/v1/stocks/recommendations`

종목 추천 목록 조회 — 핵심 엔드포인트

| 파라미터 | 타입 | 기본값 | 제약 | 설명 |
|----------|------|--------|------|------|
| `date` | string | None | YYYY-MM-DD | 조회 날짜 (생략 시 최신) |
| `model_version` | string | `latest` | — | 모델 버전 |
| `sector` | string | None | — | 섹터 필터 (정확일치) |
| `top_k` | int | 20 | 0~500 | 상위 N개 (0=전체) |
| `min_score` | float | 0.0 | 0~100 | 최소 점수 필터 |

**SQL 로직**:
```sql
SELECT date, ticker, name, sector, mid_sector, close,
       ROUND(prob_lgbm,6), ROUND(prob_xgb,6), ROUND(prob_cat,6),
       ROUND(prob_ensemble,6), ROUND(score,1),
       tier, rank_in_date, total_in_date, model_version
FROM scores
WHERE model_version = ?
  AND CAST(date AS VARCHAR) = ?
  AND score >= ?
  [AND sector = ?]
ORDER BY score DESC
[LIMIT top_k]
```

- **응답**: `StockScoreList { date, model_version, total, items: [StockScore, ...] }`
- **에러**: 결과 없음 → 404

---

#### GET `/api/v1/stocks/{ticker}/history`

특정 종목의 날짜별 점수 이력

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `ticker` | path | 종목코드 |
| `model_version` | query | 모델 버전 |
| `start_date` | query | 시작일 YYYY-MM-DD |
| `end_date` | query | 종료일 YYYY-MM-DD |

- **로직**: ticker를 6자리 zero-pad 후 날짜 범위 필터, 오름차순 정렬
- **응답**: `StockHistory { ticker, model_version, total, items: [StockHistoryItem, ...] }`

---

#### GET `/api/v1/stocks/sectors/summary`

섹터별 평균 점수 요약

| 파라미터 | 설명 |
|----------|------|
| `date` | 조회 날짜 (생략 시 최신) |
| `model_version` | 모델 버전 |

**SQL 로직**:
```sql
SELECT COALESCE(sector, '미분류') AS sector,
       COUNT(*) AS stock_count,
       ROUND(AVG(score),1) AS avg_score,
       ROUND(MAX(score),1) AS max_score,
       ROUND(MIN(score),1) AS min_score,
       SUM(CASE WHEN tier='A' THEN 1 ELSE 0 END) AS tier_a_count,
       CAST(date AS VARCHAR), model_version
FROM scores
WHERE model_version = ? AND CAST(date AS VARCHAR) = ?
GROUP BY sector, date, model_version
ORDER BY avg_score DESC
```

- **응답**: `SectorSummaryList { date, model_version, total, items: [SectorSummaryItem, ...] }`

---

#### GET `/api/v1/stocks/search`

종목 검색 (티커·회사명 키워드)

| 파라미터 | 제약 | 설명 |
|----------|------|------|
| `q` | min_length=1, 필수 | 검색 키워드 |
| `model_version` | — | 모델 버전 |
| `limit` | 1~100 | 최대 결과 수 |

**SQL 로직** (각 종목의 최신 날짜 기준):
```sql
SELECT s.ticker, s.name, s.sector, s.mid_sector,
       ROUND(s.score,1) AS score, s.tier, s.model_version,
       CAST(s.date AS VARCHAR) AS latest_date
FROM scores s
INNER JOIN (
    SELECT ticker, MAX(date) AS max_date
    FROM scores WHERE model_version = ?
    GROUP BY ticker
) latest ON s.ticker = latest.ticker AND s.date = latest.max_date
WHERE s.model_version = ?
  AND (s.ticker ILIKE ? OR s.name ILIKE ?)
ORDER BY s.score DESC
LIMIT ?
```

- **응답**: `StockSearchList { query, total, items: [StockSearchResult, ...] }`
- **캐시**: 120초

---

### 3.3 포트폴리오 API — `/api/v1/portfolio`

#### GET `/api/v1/portfolio/backtest/summary`

v7·v8 백테스트 성과 요약

- **로직**:
  - `models/v8_walk_forward/results/wf_performance_summary.txt` 전문 읽기
  - `models/backtest_comparison/comparison_summary.csv` → JSON 변환
- **응답**: `BacktestSummaryResponse { v8_walk_forward: "...", comparison: [...] }`
- **캐시**: 600초

---

#### GET `/api/v1/portfolio/backtest/monthly`

v8 Walk-Forward 월별 수익률 raw 데이터

- **로직**: `wf_portfolio_monthly_returns.csv` 로드, `source: "v8_walk_forward"` 태그 추가
- **응답**: `BacktestMonthlyResponse { data: [...] }` — 프론트 차트 연결용

---

#### GET `/api/v1/portfolio/kospi200`

KOSPI 200 맞춤형 Top 10 자동 포트폴리오

| 파라미터 | 선택지 | 설명 |
|----------|--------|------|
| `type` | `growth` \| `stable` | 포트폴리오 유형 |
| `model_version` | string | 모델 버전 |

**비즈니스 로직**:

| 유형 | 필터 조건 | 정렬 |
|------|-----------|------|
| `growth` (성장형) | KOSPI 200 전체 종목 | score 내림차순 Top 10 |
| `stable` (안정형) | Tier A·B + 최신 분기 PBR < 1.5 | score 내림차순 Top 10 |

**growth SQL**:
```sql
SELECT s.ticker, s.name, s.sector, CAST(s.score AS FLOAT), s.tier, NULL AS pbr
FROM scores s
INNER JOIN read_csv_auto('{seed_path}') k ON s.ticker = k.ticker
WHERE s.model_version = ? AND CAST(s.date AS VARCHAR) = ?
ORDER BY s.score DESC
LIMIT 10
```

**stable SQL** (PBR CTE 포함):
```sql
WITH latest_finance AS (
    SELECT f.ticker, CAST(f.pbr AS FLOAT) AS pbr
    FROM finance f
    INNER JOIN (SELECT ticker, MAX(year*10+quarter) AS max_yq FROM finance GROUP BY ticker) lf
    ON f.ticker = lf.ticker AND (f.year*10+f.quarter) = lf.max_yq
)
SELECT s.ticker, s.name, s.sector, score, s.tier, fi.pbr
FROM scores s
INNER JOIN read_csv_auto('{seed_path}') k ON s.ticker = k.ticker
LEFT JOIN latest_finance fi ON s.ticker = fi.ticker
WHERE s.model_version = ? AND s.date = ? AND s.tier IN ('A','B') AND fi.pbr < 1.5
ORDER BY s.score DESC LIMIT 10
```

- **응답**: `PortfolioResponse { type, date, model_version, total, items: [PortfolioItem, ...] }`
- **캐시**: 300초

---

### 3.4 차트 API — `/api/v1/chart`

#### GET `/api/v1/chart/{ticker}`

종목 캔들스틱 + 이동평균 데이터

| 파라미터 | 선택지 | 기본값 | 설명 |
|----------|--------|--------|------|
| `period` | `1m` `3m` `6m` `1y` `3y` `all` | `1y` | 조회 기간 |

**비즈니스 로직**:
- `prices` 테이블의 최신 날짜 기준으로 `period`에 해당하는 날짜 이전 데이터 절단
- OHLCV + `amount` + `market_cap` + MA(5/20/60/120) 반환
- `scores` 테이블에서 종목명 보조 조회

**응답**: `ChartResponse { ticker, name, period, total, items: [CandleItem, ...] }`

각 `CandleItem`: `date, open, high, low, close, volume, amount, market_cap, ma5, ma20, ma60, ma120`

- **캐시**: 300초
- **에러**: 종목 없음 → 404, 잘못된 period → 422

---

### 3.5 재무 API — `/api/v1/finance`

#### GET `/api/v1/finance/{ticker}`

종목 전체 분기별 재무 이력

| 파라미터 | 제약 | 기본값 | 설명 |
|----------|------|--------|------|
| `limit` | 1~100 | 20 | 최근 N개 분기 |

- **로직**: `ORDER BY year DESC, quarter DESC LIMIT ?`
- **응답**: `FinanceResponse { ticker, name, total, items: [FinanceItem, ...] }`
- **캐시**: 600초

---

#### GET `/api/v1/finance/{ticker}/latest`

종목 최신 분기 재무 요약

- **로직**: 가장 최근 분기 1개 조회 — PER, PBR, EPS, ROE, 부채비율, 영업이익률, 매출성장률, 재무점수 포함
- **응답**: `FinanceLatest { ticker, name, year, quarter, base_date, per, pbr, eps, roe, debt_ratio, op_margin, rev_growth_yoy, finance_score }`
- **캐시**: 600초

---

### 3.6 스크리너 API — `/api/v1/screener`

#### GET `/api/v1/screener`

ML 점수 + 재무 조건 복합 스크리너

**ML 조건 파라미터**

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `model_version` | `latest` | 모델 버전 |
| `min_score` | 0.0 | 최소 ML 점수 |
| `tier` | None | A \| B \| C \| D |
| `sector` | None | 섹터명 (부분 일치 ILIKE) |

**재무 조건 파라미터**

| 파라미터 | 설명 |
|----------|------|
| `max_per` | 최대 PER |
| `max_pbr` | 최대 PBR |
| `min_roe` | 최소 ROE (%) |
| `max_debt_ratio` | 최대 부채비율 (%) |
| `min_op_margin` | 최소 영업이익률 (%) |
| `min_rev_growth` | 최소 매출성장률 YoY (%) |
| `min_finance_score` | 최소 재무 점수 |

**정렬·페이지 파라미터**

| 파라미터 | 허용값 | 기본값 | 설명 |
|----------|--------|--------|------|
| `sort_by` | `composite_score` `score` `finance_score` `roe` `per` `pbr` `rev_growth_yoy` | `composite_score` | 정렬 기준 |
| `limit` | 1~200 | 50 | 최대 결과 수 |

**핵심 비즈니스 로직 — composite_score**:

$$\text{composite\_score} = \text{ML score} \times 0.6 + \text{finance\_score} \times 0.4$$

- `finance_score`가 NULL인 경우 **50점으로 대체** (중립값)
- 최신 재무 분기는 `MAX(year*10+quarter)` 방식으로 서브쿼리 결정

**SQL 구조**:
```sql
SELECT s.ticker, name, s.sector,
       ROUND(s.score, 1) AS score, s.tier,
       fi.per, fi.pbr, fi.roe, fi.debt_ratio, fi.op_margin,
       fi.rev_growth_yoy, ROUND(fi.finance_score,1),
       ROUND(s.score * 0.6 + COALESCE(fi.finance_score, 50.0) * 0.4, 1) AS composite_score
FROM scores s
LEFT JOIN (최신분기_재무_서브쿼리) fi ON s.ticker = fi.ticker
WHERE [ML 조건] [AND 재무 조건]
ORDER BY {sort_col} DESC NULLS LAST
LIMIT ?
```

- **응답**: `ScreenerResponse { total, items: [ScreenerItem, ...] }`
- **캐시**: 120초

---

### 3.7 종목 비교 API — `/api/v1/compare`

#### GET `/api/v1/compare`

2~10개 종목의 ML 점수 이력 + 재무 지표 비교

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `tickers` | 필수 | 쉼표 구분 종목코드 (예: `005930,000660`) |
| `model_version` | — | 모델 버전 |
| `period` | — | `3m` `6m` `1y` `3y` `all` (기본 `1y`) |

**비즈니스 로직**:
- 각 티커별로 `scores` 테이블에서 점수 이력 조회
- `scores` 최신 날짜 기준 `period_days`일 이전까지 필터
- 각 티커의 최신 분기 재무 데이터(`finance` 테이블) 병렬 조회
- 종목별 `{ ticker, name, sector, latest_score, tier, score_history: [{date,score},...], finance }` 구조로 반환

**제약**:
- 최소 2개, 최대 10개
- 잘못된 ticker 수 → 422

**응답**: `CompareResponse { tickers, total, items: [CompareItem, ...] }`
- **캐시**: 120초

---

### 3.8 마켓 레이더 API — `/api/v1/market`

#### GET `/api/v1/market/regime`

시장 국면(기상도) 조회

| 파라미터 | 설명 |
|----------|------|
| `model_version` | 모델 버전 |

**핵심 비즈니스 로직 — 시장 국면 판정**:

최신 영업일의 전체 종목 중 **Tier A 비율**로 3단계 시장 국면 결정:

| Tier A 비율 | status | weather | 메시지 |
|------------|--------|---------|--------|
| **10% 이상** | `greed` | ☀️ 맑음 | 상승 모멘텀이 강합니다. 적극적인 투자가 유리한 국면입니다. |
| **5~10% 미만** | `neutral` | ☁️ 흐림 | 방향성 탐색 구간입니다. 선별적인 종목 접근이 필요합니다. |
| **5% 미만** | `fear` | 🌧️ 비 | 시장 변동성이 커지고 있습니다. 현금 비중 확대를 권장합니다. |

**SQL**:
```sql
SELECT COUNT(*) AS total_count,
       SUM(CASE WHEN tier = 'A' THEN 1 ELSE 0 END) AS tier_a_count
FROM scores
WHERE model_version = ? AND CAST(date AS VARCHAR) = ?
```

- **응답**: `MarketRegimeResponse { date, model_version, total_count, tier_a_count, tier_a_ratio, status, weather, message }`
- **캐시**: 300초

---

### 3.9 커뮤니티 게시판 API — `/api/v1/board`

**이중 DB 아키텍처**: DuckDB(OLAP 분석) + SQLite(OLTP 트랜잭션) 분리

#### GET `/api/v1/board/posts/{ticker}` — 게시글 목록

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `page` | 1 | 페이지 번호 |
| `page_size` | 20 | 페이지당 게시글 수 (최대 100) |

- 최신순 정렬, 댓글 수 포함 반환
- **응답**: `PostListResponse { ticker, total, page, page_size, items }`

---

#### POST `/api/v1/board/posts` — 게시글 작성

**Body**: `PostCreate { ticker, author_id, title, content }`

- SQLite에 INSERT, 작성된 게시글 상세 반환
- HTTP 201 Created

---

#### GET `/api/v1/board/posts/detail/{post_id}` — 게시글 상세

- 호출 시 **조회수(views) +1** 자동 증가
- 본문(content) 포함 반환

---

#### DELETE `/api/v1/board/posts/{post_id}` — 게시글 삭제

| 파라미터 | 설명 |
|----------|------|
| `author_id` | 삭제 요청자 ID (본인 확인용) |

- 작성자 불일치 → **403 Forbidden**
- 게시글 없음 → 404
- 연결 댓글·좋아요 **CASCADE 삭제**

---

#### POST `/api/v1/board/comments` — 댓글 작성

**Body**: `CommentCreate { post_id, author_id, content }`

- 존재하지 않는 post_id → 404
- HTTP 201 Created

---

#### GET `/api/v1/board/comments/{post_id}` — 댓글 목록

- 작성 순서(오름차순) 정렬
- **응답**: `CommentListResponse { post_id, total, items }`

---

#### POST `/api/v1/board/posts/{post_id}/like` — 좋아요 토글

| 상태 | 결과 |
|------|------|
| 아직 좋아요 안 함 | +1, `liked: true` 반환 |
| 이미 좋아요 함 | -1, `liked: false` 반환 |

- DB `PRIMARY KEY (post_id, author_id)`로 중복 좋아요 차단
- **응답**: `LikeResponse { post_id, author_id, liked, likes }`

---

## 4. 인증/사용자 서버 (포트 8000)

**`db/server.py`** — FastAPI 인증 서버

### 4.1 인증 흐름 다이어그램

```
[회원가입]
이메일 입력 → POST /auth/check-email
  └─ 중복 검사 (PostgreSQL)
  └─ 6자리 코드 생성 → Redis setex verify:{email} 180초
  └─ SMTP 이메일 발송 (Gmail SSL 465)
  ↓
코드 입력 → POST /auth/verify-code
  └─ Redis에서 코드 검증
  └─ Redis setex confirmed:{email} 300초
  ↓
가입 완료 → POST /auth/register
  └─ confirmed:{email} 존재 확인
  └─ 닉네임 중복 검사
  └─ bcrypt 해시 저장 → PostgreSQL users 테이블
  └─ Redis confirmed 키 삭제

[로그인]
POST /auth/login
  └─ bcrypt verify
  └─ UUID 세션 토큰 발급 → Redis setex session:{token} 3600초
  └─ {session_token, nickname} 반환

[비밀번호 변경 — 로그인 상태]
POST /auth/reset-password (Header: session_token)
  └─ get_current_user: Redis에서 session:{token} → email 조회
  └─ 현재 비밀번호 bcrypt 검증
  └─ 새 비밀번호 해시 → DB 업데이트

[비밀번호 재설정 — 이메일 인증]
POST /auth/reset-password-via-email
  └─ Redis confirmed:{email} 확인
  └─ 새 비밀번호 해시 → DB 업데이트
  └─ Redis confirmed 키 삭제
```

### 4.2 인증 API 엔드포인트

| Method | Path | Body / Header | 설명 |
|--------|------|---------------|------|
| POST | `/auth/check-email` | `email` (query) | 이메일 중복 검사 + 인증코드 발송 |
| POST | `/auth/verify-code` | `EmailVerification {email, code}` | 인증코드 검증 |
| POST | `/auth/register` | `UserCreate {email, nickname, password}` | 회원가입 |
| POST | `/auth/login` | `UserLogin {email, password}` | 로그인 → 세션 토큰 |
| POST | `/auth/reset-password` | `PasswordResetRequest` + `session_token` Header | 비밀번호 변경 (로그인 상태) |
| POST | `/auth/reset-password-via-email` | `PasswordResetEmailRequest {email, code, new_password}` | 비밀번호 재설정 (이메일 인증) |

### 4.3 비밀번호 정책

```regex
^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,24}$
```

- 영문 + 숫자 + 특수문자(@$!%*#?&) 필수 포함
- 8~24자

### 4.4 SMTP 이메일 발송

- Gmail SMTP SSL (포트 465)
- 환경변수: `SMTP_USER`, `SMTP_PASSWORD`
- 발송 실패 시 500 에러 반환

---

## 5. 서비스 레이어 — `services/data.py`

모든 DuckDB 쿼리와 Redis 캐시 로직을 담당하는 단일 서비스 파일 (878줄).

### 5.1 DuckDB 싱글턴 연결

```python
_duckdb_con: duckdb.DuckDBPyConnection | None = None
_duckdb_lock = threading.Lock()
```

- 앱 시작 시 `init_duckdb()` 단 1회 호출
- 이후 모든 요청은 동일 연결 객체 재사용 (read_only=True, 동시 읽기 안전)
- Double-checked locking 패턴으로 스레드 안전 보장

### 5.2 Redis 캐시 래퍼

```python
def _cached(fn_name, fetch_fn, ttl=REDIS_CACHE_TTL, **kwargs):
    key = "ml_api:" + md5(JSON(fn_name + kwargs))
    if redis.get(key): return json.loads(hit)
    result = fetch_fn()
    redis.setex(key, ttl, json.dumps(result))
    return result
```

- 캐시 키: `ml_api:` + 함수명 + 파라미터의 MD5 해시
- Redis 연결 실패 시 **graceful fallback** — 캐시 없이 DuckDB 직접 조회
- Redis 재연결 억제: 실패 후 30초간 재시도 안 함

### 5.3 `latest` 버전 자동 해석

```python
def _resolve_version(model_version: str) -> str:
    if model_version != "latest":
        return model_version
    row = con.execute(
        "SELECT model_version FROM scores ORDER BY inserted_at DESC LIMIT 1"
    ).fetchone()
    return row[0]
```

모든 public 함수가 `_resolve_version` 호출 → `"latest"` 전달 시 자동으로 가장 최근 버전 선택

### 5.4 Public 함수 목록

| 함수 | 캐시 TTL | 설명 |
|------|---------|------|
| `get_available_versions()` | 300초 | 모델 버전 목록 |
| `get_available_dates(model_version)` | 60초 | 날짜 목록 |
| `get_recommendations(date, model_version, sector, top_k, min_score)` | 60초 | 추천 목록 |
| `get_stock_history(ticker, model_version, start_date, end_date)` | 60초 | 종목 점수 이력 |
| `get_sector_summary(date, model_version)` | 60초 | 섹터별 요약 |
| `search_stocks(q, model_version, limit)` | 120초 | 종목 검색 |
| `get_chart(ticker, period)` | 300초 | OHLCV + 이동평균 |
| `get_finance(ticker, limit)` | 600초 | 분기별 재무 이력 |
| `get_finance_latest(ticker)` | 600초 | 최신 분기 재무 |
| `screen_stocks(...)` | 120초 | 복합 스크리너 |
| `compare_stocks(tickers, model_version, period_days)` | 120초 | 종목 비교 |
| `get_backtest_summary()` | 600초 | 백테스트 성과 요약 |
| `get_backtest_monthly_returns()` | 600초 | 월별 수익률 |
| `get_market_regime(model_version)` | 300초 | 시장 국면 판정 |
| `get_kospi200_portfolio(portfolio_type, model_version)` | 300초 | KOSPI200 포트폴리오 |

---

## 6. 머신러닝 전처리 파이프라인

세 개의 `precompute_*.py` 스크립트가 원천 데이터를 처리하여 `scores.duckdb`에 적재한다.  
**실행 순서**: `precompute_chart.py` → `precompute_finance.py` → `precompute_scores.py`

### 6.1 ML 점수 적재 — `precompute_scores.py`

```
LightGBM predictions.parquet
XGBoost  predictions.parquet  ─→ 병합 ─→ 앙상블 ─→ 점수화 ─→ scores.duckdb
CatBoost predictions.parquet
```

**Step 1 — parquet 3종 병합** (`load_and_merge`)

```python
df_l = pd.read_parquet(lgbm_path, columns=["date","종목코드","wics_large_name","close","prob_lgbm"])
df_x = pd.read_parquet(xgb_path,  columns=["date","종목코드","prob_xgb"])
df_c = pd.read_parquet(cat_path,  columns=["date","종목코드","prob_cat"])
df = df_l.merge(df_x, on=["date","종목코드"]).merge(df_c, on=["date","종목코드"])
```

**Step 2 — seed.csv join** (`join_seed`)

- `seed.csv` (ticker, name, wics_large_name, wics_mid_name) LEFT JOIN
- parquet 섹터 값 우선, NULL이면 seed로 보완

**Step 3 — 점수 계산** (`compute_scores`)

```python
# 앙상블 확률
prob_ensemble = (prob_lgbm + prob_xgb + prob_cat) / 3.0

# 날짜별 내림차순 순위
rank_in_date = groupby("date")["prob_ensemble"].rank(ascending=False, method="min")

# 1~100점 백분위 점수
pct = (rank_in_date - 1) / (total_in_date - 1).clip(lower=1)
score = ((1.0 - pct) * 100).clip(0, 100).round(1)

# 티어 분류
tier = pd.cut(score, bins=[-0.1, 40, 60, 80, 100.1], labels=["D","C","B","A"])
```

**티어 기준표**:

| 점수 범위 | 티어 | 의미 |
|-----------|------|------|
| 80.1 ~ 100 | **A** | 최우량 (상위 20%) |
| 60.1 ~ 80 | **B** | 우량 |
| 40.1 ~ 60 | **C** | 보통 |
| 0 ~ 40 | **D** | 관심 요망 |

**Step 4 — DuckDB 저장** (`save_to_duckdb`)

- `--overwrite` 플래그: 기존 버전 데이터 DELETE 후 재적재
- 버전 중복 시 자동 SKIP (멱등성 보장)

**실행 예시**:
```bash
# v7 기본 경로 (자동 감지)
python precompute_scores.py --model-version v7

# 경로 직접 지정
python precompute_scores.py --model-version v8 \
    --lgbm path/to/lgbm.parquet \
    --xgb  path/to/xgb.parquet \
    --cat  path/to/cat.parquet

# 재적재
python precompute_scores.py --model-version v7 --overwrite
```

---

### 6.2 재무 스코어 적재 — `precompute_finance.py`

`financial_indicators_clean.csv` → `finance` 테이블 + 재무 점수 산정

**재무 스코어 산정 기준 (100점 만점)**:

| 지표 | 가중치 | 방향 | 기준 |
|------|--------|------|------|
| ROE (자기자본이익률) | **25점** | 높을수록 좋음 | 수익성 핵심 지표 |
| 부채비율 | **20점** | 낮을수록 좋음 ↓ | 재무 안정성 |
| 영업이익률 | **20점** | 높을수록 좋음 | 본업 수익성 |
| 매출액증가율 (YoY) | **15점** | 높을수록 좋음 | 성장성 |
| PBR | **10점** | 낮을수록 좋음 ↓ | 가치평가 |
| 유동비율 | **10점** | 높을수록 좋음 | 단기 지급능력 |

**알고리즘 (`compute_finance_score`)**:

```python
for (year, quarter), group in df.groupby(["year","quarter"]):
    for col, weight in SCORE_WEIGHTS.items():
        # 분기 내 상대 백분위 (0~100)
        rank_pct = series.rank(pct=True, ascending=not lower_is_better) * 100
        rank_pct.fillna(50.0)  # NaN → 중립값 50
    finance_score = sum(rank_pct * weight/total).clip(0,100).round(1)
```

- 절대 기준이 아닌 **동일 분기 내 상대 순위** 기반
- NaN 값은 50점(중립)으로 처리
- PRIMARY KEY `(ticker, year, quarter)` — 중복 INSERT 무시 (`INSERT OR IGNORE`)

---

### 6.3 가격·이동평균 적재 — `precompute_chart.py`

`stock_data_clean.csv` → `prices` 테이블

**처리 흐름**:

1. CSV 로드: `종목코드, 일자, 시가, 고가, 저가, 종가, 거래량, 거래대금, 시가총액`
2. ticker 6자리 zero-pad
3. 날짜 정수(`YYYYMMDD`) → `'YYYY-MM-DD'` 문자열 변환
4. 이동평균 계산:
   ```python
   for win in [5, 20, 60, 120]:
       df[f"ma{win}"] = df.groupby("ticker")["close"] \
           .transform(lambda s: s.rolling(win, min_periods=1).mean().round(2))
   ```
5. PRIMARY KEY `(ticker, date)` — `INSERT OR IGNORE`

---

## 7. 데이터 모델 및 스키마

### 7.1 Pydantic 응답 스키마 (`FastAPI/schemas/`)

#### `StockScore` — 단일 종목 추천 레코드

```python
class StockScore(BaseModel):
    date, ticker, name, sector, mid_sector, close
    prob_lgbm, prob_xgb, prob_cat   # 0~1
    prob_ensemble                    # (lgbm+xgb+cat)/3
    score        # 1~100
    tier         # A/B/C/D
    rank_in_date, total_in_date
    model_version
```

#### `MarketRegimeResponse` — 시장 국면

```python
class MarketRegimeResponse(BaseModel):
    date, model_version
    total_count, tier_a_count
    tier_a_ratio        # %
    status              # greed | neutral | fear
    weather             # 맑음 | 흐림 | 비
    message             # 한국어 안내 메시지
```

#### `PortfolioItem` — 포트폴리오 종목

```python
class PortfolioItem(BaseModel):
    rank, ticker, name, sector
    score, tier
    pbr     # stable 타입에서만 반환
```

#### `ScreenerItem` — 스크리너 결과

```python
class ScreenerItem(BaseModel):
    ticker, name, sector, score, tier, latest_date
    per, pbr, roe, debt_ratio, op_margin, rev_growth_yoy
    finance_score
    composite_score   # ML*0.6 + Finance*0.4
```

### 7.2 SQLAlchemy 모델 (`db/db/models.py`)

```python
class User:
    user_id, email(UNIQUE), hashed_password
    nickname(UNIQUE), is_active, is_verified, created_at
    → watchlist: List[UserWatchlist]
    → notifications: List[Notification]

class UserWatchlist:
    id, user_id(FK), ticker

class Notification:
    id, user_id(FK), ticker, title
    sentiment_label    # FinBERT 감성 분석 결과
    is_read, created_at
```

---

## 8. 캐싱 전략

### 캐시 키 생성

```
ml_api:{MD5(JSON({ "fn": 함수명, **파라미터 }))}
```

- 동일 함수 + 동일 파라미터 조합 → 동일 캐시 키
- 파라미터가 하나라도 다르면 별도 캐시 엔트리

### TTL 설계 의도

| 엔드포인트 | TTL | 이유 |
|-----------|-----|------|
| 버전 목록 | 300초 | 모델 추가가 드물게 발생 |
| 시장 국면 | 300초 | 영업일 기준 하루 1회 업데이트 |
| KOSPI200 포트폴리오 | 300초 | 동일 |
| 차트 / 재무 | 300~600초 | 일별·분기별 데이터 |
| 추천 / 스크리너 / 비교 | 60~120초 | 자주 조회되는 핵심 데이터 |

### Graceful Fallback

```
Redis 연결 시도
  → 성공: 캐시 히트 시 즉시 반환, 미스 시 DuckDB 조회 후 저장
  → 실패: DuckDB 직접 조회 (서비스 중단 없음)
  → 실패 후 30초간 Redis 재시도 억제
```

---

## 9. 주요 비즈니스 로직 요약

### 9.1 ML 앙상블 점수화 파이프라인

```
3개 모델 예측 확률
  LightGBM (prob_lgbm)
  XGBoost  (prob_xgb)    → 단순 평균 → prob_ensemble → 날짜별 백분위 → 1~100점 → A/B/C/D 티어
  CatBoost (prob_cat)
```

- **단순 평균 앙상블**: 편향 없이 세 모델의 예측을 동등하게 반영
- **백분위 점수**: 절대적 확률이 아닌 **상대 순위** 기반 → 날짜별 시장 상황을 반영한 공정한 비교

### 9.2 재무 점수화

- **분기 내 상대 백분위**: 같은 분기 내 모든 종목 중 상위 몇 %인지로 점수 결정
- **가중합산**: ROE(25%) + 부채비율(20%) + 영업이익률(20%) + 매출성장률(15%) + PBR(10%) + 유동비율(10%)
- **결측치 처리**: NaN → 50점 (불이익 없이 중립 처리)

### 9.3 복합 스코어 (Composite Score)

$$\text{composite\_score} = \text{ML score} \times 0.6 + \text{finance\_score} \times 0.4$$

- ML 점수(미래 수익성 예측)에 더 큰 가중치 부여
- 재무 점수(현재 펀더멘털)로 보완

### 9.4 시장 국면(기상도)

- Tier A(최상위 20% 이상 점수) 종목의 **시장 내 비율**로 전체 시장 심리 측정
- 단일 지표(Tier A 비율)의 임계값 기반 3단계 분류 → 직관적 시각화 (맑음/흐림/비)

### 9.5 KOSPI 200 맞춤형 포트폴리오

| 전략 | 설계 철학 |
|------|-----------|
| **성장형** | AI 모델이 가장 유망하다고 판단한 KOSPI 200 종목 Top 10 순수 선택 |
| **안정형** | 고점수(Tier A·B) + 저평가(PBR<1.5) 두 조건의 교집합 → 리스크 관리 우선 |

### 9.6 인증 보안 설계

| 계층 | 보안 조치 |
|------|-----------|
| 비밀번호 저장 | bcrypt 단방향 해시 |
| 세션 관리 | UUID 기반 랜덤 토큰 + Redis TTL 1시간 |
| 이메일 인증 | 6자리 난수 코드 + Redis TTL 3분 (단발성) |
| 인증 완료 플래그 | Redis TTL 5분 (회원가입 완료 전 만료) |
| 비밀번호 정책 | 영문+숫자+특수문자 조합 8~24자 |

---

## 10. 자동 포트폴리오 구성 로직 상세

### 10.1 개요

자동 포트폴리오 기능은 **KOSPI 상장 종목**(seed.csv 기준 785개)과 ML 앙상블 점수·재무 지표를 결합하여 사용자 투자 성향에 맞는 **Top 10 종목**을 자동 구성한다. 사용자가 별도의 조건을 입력할 필요 없이 `type` 파라미터 하나로 두 가지 전략 중 선택한다.

### 10.2 종목 유니버스 — seed.csv

```
e:\Capstone Data\preprocessing\seed.csv
총 2,365개 종목 (KOSPI 785개 + KOSDAQ 1,580개)
```

| 컬럼 | 설명 |
|------|------|
| `exchange` | 거래소 (KOSPI / KOSDAQ) |
| `ticker` | 종목코드 (6자리) |
| `name` | 종목명 |
| `wics_large` / `wics_large_name` | WICS 대분류 코드·명칭 |
| `wics_mid` / `wics_mid_name` | WICS 중분류 코드·명칭 |

**포트폴리오 유니버스**: `INNER JOIN read_csv_auto(seed.csv) k ON s.ticker = k.ticker`  
→ seed.csv에 등재된 KOSPI 종목만 대상 (KOSDAQ 제외됨)

> **설계 의도**: KOSPI 종목은 KOSDAQ 대비 상장 요건이 엄격하고 기관·외국인 투자 비중이 높아 유동성과 안정성이 상대적으로 높다. 이 유니버스를 베이스라인으로 삼아 두 가지 전략을 적용한다.

---

### 10.3 두 가지 포트폴리오 전략 비교

| 구분 | `growth` (성장형) | `stable` (안정형) |
|------|------------------|------------------|
| **투자 철학** | AI 모델이 단기 상승 가능성이 높다고 판단한 종목 집중 | 고점수 종목 중 재무적으로 저평가된 방어적 종목 선별 |
| **1차 필터** | seed.csv KOSPI 전체 | seed.csv KOSPI 전체 |
| **2차 필터** | 없음 (전체 대상) | Tier A 또는 B (score ≥ 60점) |
| **3차 필터** | 없음 | 최신 분기 PBR < 1.5 |
| **정렬 기준** | ML score 내림차순 | ML score 내림차순 |
| **최종 선택** | Top 10 | Top 10 |
| **반환 필드** | ticker, name, sector, score, tier | ticker, name, sector, score, tier, **pbr** |
| **적합 투자자** | 공격적 투자자, 단기 모멘텀 추구 | 보수적 투자자, 가치투자 성향 |

---

### 10.4 성장형(growth) 포트폴리오 상세 로직

#### 처리 흐름

```
scores 테이블 (최신 날짜, 해당 model_version)
        ↓
INNER JOIN seed.csv (ticker 기준 — KOSPI 상장 종목만 통과)
        ↓
ORDER BY score DESC
        ↓
LIMIT 10 → Top 10 반환
```

#### SQL

```sql
SELECT
    s.ticker,
    s.name,
    s.sector,
    CAST(s.score AS FLOAT) AS score,
    s.tier,
    NULL AS pbr
FROM scores s
INNER JOIN read_csv_auto('{seed_csv_path}') k
    ON s.ticker = k.ticker
WHERE s.model_version = ?
  AND CAST(s.date AS VARCHAR) = ?
ORDER BY s.score DESC
LIMIT 10
```

#### 결과 예시

| rank | ticker | name | sector | score | tier |
|------|--------|------|--------|-------|------|
| 1 | 005930 | 삼성전자 | IT | 97.3 | A |
| 2 | 000660 | SK하이닉스 | IT | 95.1 | A |
| 3 | ... | ... | ... | ... | A |

---

### 10.5 안정형(stable) 포트폴리오 상세 로직

#### 처리 흐름

```
finance 테이블
  → 종목별 최신 분기 PBR 추출 (CTE: latest_finance)
        ↓
scores 테이블 (최신 날짜, 해당 model_version)
        ↓
INNER JOIN seed.csv (KOSPI 상장 종목 필터)
LEFT  JOIN latest_finance (PBR 데이터 결합)
        ↓
WHERE tier IN ('A', 'B')   ← ML 점수 상위 40% (score ≥ 60)
  AND pbr < 1.5             ← 재무 저평가 (장부가 대비 시장가 1.5배 미만)
        ↓
ORDER BY score DESC
        ↓
LIMIT 10 → Top 10 반환
```

#### SQL (CTE 포함)

```sql
WITH latest_finance AS (
    -- 종목별 가장 최근 분기 PBR만 추출
    SELECT
        f.ticker,
        CAST(f.pbr AS FLOAT) AS pbr
    FROM finance f
    INNER JOIN (
        SELECT ticker, MAX(year * 10 + quarter) AS max_yq
        FROM finance
        GROUP BY ticker
    ) lf ON f.ticker = lf.ticker
         AND (f.year * 10 + f.quarter) = lf.max_yq
)
SELECT
    s.ticker,
    s.name,
    s.sector,
    CAST(s.score AS FLOAT) AS score,
    s.tier,
    fi.pbr
FROM scores s
INNER JOIN read_csv_auto('{seed_csv_path}') k
    ON s.ticker = k.ticker
LEFT JOIN latest_finance fi
    ON s.ticker = fi.ticker
WHERE s.model_version = ?
  AND CAST(s.date AS VARCHAR) = ?
  AND s.tier IN ('A', 'B')      -- score 60점 이상
  AND fi.pbr < 1.5              -- PBR 저평가
ORDER BY s.score DESC
LIMIT 10
```

#### 최신 분기 결정 방식

```python
# year=2024, quarter=3 → 20243
# year=2024, quarter=4 → 20244
# MAX(year*10 + quarter) → 가장 최근 분기 자동 선택
MAX(year * 10 + quarter)
```

이 방식은 연도·분기 간 경계를 정수 비교만으로 해결한다. 예: 2023Q4(20234) < 2024Q1(20241) ✓

---

### 10.6 티어(Tier) 기준과 포트폴리오 필터 관계

```
score 계산: (1 - (rank-1)/(total-1)) * 100

점수 → 티어 분류:
┌─────────────────────────────────────────────────────────────┐
│  0  ── 40  ── 60  ── 80 ── 100                              │
│  [──D──][────C────][────B────][────A────]                   │
│                                                             │
│  growth 필터: 전체 (D·C·B·A 모두 포함)                       │
│  stable 필터: [────B────][────A────] 만 통과                 │
└─────────────────────────────────────────────────────────────┘
```

| 티어 | 점수 범위 | 의미 | stable 포함 여부 |
|------|-----------|------|-----------------|
| **A** | 80.1 ~ 100 | 최우량 (날짜 내 상위 20%) | ✅ |
| **B** | 60.1 ~ 80 | 우량 | ✅ |
| **C** | 40.1 ~ 60 | 보통 | ❌ |
| **D** | 0 ~ 40 | 관심 필요 | ❌ |

---

### 10.7 PBR 1.5 임계값의 의미

**PBR(Price-to-Book Ratio)** = 주가 ÷ 주당 순자산

| PBR 범위 | 해석 |
|----------|------|
| < 1.0 | 시장가 < 장부가 — 극도 저평가 또는 구조적 문제 |
| 1.0 ~ 1.5 | **안정형 포트폴리오 대상** — 저평가 영역, 하방 리스크 제한적 |
| 1.5 ~ 3.0 | 적정 평가 |
| > 3.0 | 고평가 또는 성장 프리미엄 |

> **설계 의도**: PBR < 1.5 조건은 AI 모델이 높게 평가한 종목(Tier A·B) 중에서도 **현재 가격이 내재가치 대비 크게 부풀려지지 않은 종목**만 선별하여 하방 리스크를 줄이는 역할을 한다. 가치투자 관점의 안전마진(Margin of Safety)을 확보한다.

---

### 10.8 최신 날짜 결정 로직

```python
# 포트폴리오 구성 기준일 = scores 테이블의 가장 최신 영업일
date_row = con.execute(
    "SELECT MAX(CAST(date AS VARCHAR)) FROM scores WHERE model_version = ?",
    [ver],
).fetchone()
latest_date = date_row[0]  # 예: "2024-11-01"
```

- 별도로 날짜를 입력받지 않고 **항상 가장 최신 예측 기준일** 자동 사용
- 응답에 `date` 필드로 포함되어 클라이언트가 어떤 날짜 기준인지 확인 가능

---

### 10.9 응답 구조

```json
{
  "type": "stable",
  "date": "2024-11-01",
  "model_version": "v8",
  "total": 10,
  "items": [
    {
      "rank": 1,
      "ticker": "005380",
      "name": "현대차",
      "sector": "경기소비재",
      "score": 88.5,
      "tier": "A",
      "pbr": 0.62
    },
    ...
  ]
}
```

- `rank`: 1부터 시작하는 순위 (Python에서 enumerate 주입, DB가 아닌 서비스 레이어에서 부여)
- `pbr`: growth 타입은 `null`, stable 타입은 실제 값 반환

---

### 10.10 전체 포트폴리오 구성 파이프라인 요약

```
[데이터 준비 단계] — 사전 실행 (precompute scripts)
┌─────────────────────────────────────────────────────────────────┐
│ precompute_scores.py  → DuckDB scores 테이블 (ML 점수·티어)      │
│ precompute_finance.py → DuckDB finance 테이블 (PBR 등 재무 지표) │
└────────────────────────────┬────────────────────────────────────┘
                             │
[런타임 단계] — API 호출 시 실시간 처리
                             │
          GET /api/v1/portfolio/kospi200?type=growth|stable
                             │
          ┌──────────────────▼──────────────────────┐
          │  _resolve_version("latest")              │
          │  → scores 테이블에서 최신 model_version  │
          └──────────────────┬──────────────────────┘
                             │
          ┌──────────────────▼──────────────────────┐
          │  최신 영업일 결정                         │
          │  MAX(date) WHERE model_version = ver     │
          └──────────────────┬──────────────────────┘
                             │
          ┌──────────────────▼──────────────────────┐
          │  growth: scores ⋈ seed.csv               │
          │          ORDER BY score DESC LIMIT 10    │
          │                                          │
          │  stable: scores ⋈ seed.csv               │
          │          ⋈ (finance의 최신분기 PBR)       │
          │          WHERE tier IN ('A','B')          │
          │            AND pbr < 1.5                 │
          │          ORDER BY score DESC LIMIT 10    │
          └──────────────────┬──────────────────────┘
                             │
          ┌──────────────────▼──────────────────────┐
          │  rank 필드 주입 (enumerate 1~10)          │
          │  date, model_version 필드 추가            │
          └──────────────────┬──────────────────────┘
                             │
          ┌──────────────────▼──────────────────────┐
          │  Redis 캐시 저장 (TTL 300초)             │
          └──────────────────┬──────────────────────┘
                             │
                  PortfolioResponse 반환
```

---

### 10.11 에러 처리 및 예외 케이스

| 상황 | 처리 방식 |
|------|-----------|
| scores 테이블 비어있음 | `RuntimeError` → 503 Service Unavailable |
| stable 타입 + PBR 데이터 없음 | 빈 결과 → 404 "stable 타입은 PBR 데이터가 필요합니다" |
| growth 타입 + KOSPI 종목 없음 | 빈 결과 → 404 |
| `model_version=latest` 전달 | `_resolve_version()` 자동 해석 → 실제 버전 문자열 |
| Redis 연결 실패 | Graceful fallback — 캐시 없이 DuckDB 직접 조회 |

---

*끝*
