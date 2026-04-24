# WP_Capstone

**Team.PA** 캡스톤 디자인 프로젝트 — AI 기반 주식 추천 시스템

---

## 프로젝트 구조

```
WP_Capstone/
├── Front/                  # Vue 3 + TypeScript 프론트엔드
├── Back/
│   ├── FastAPI/            # 추천·분석 API 서버 (포트 8001)
│   ├── db/                 # 인증·뉴스 서버 (포트 8000)
│   ├── go/                 # 뉴스 크롤링 파이프라인 (Go)
│   ├── Redis/              # Redis 설정 (auth / queue 인스턴스 분리)
│   └── MachineLearning/    # DuckDB 사전 계산 스크립트
└── README.md
```

---

## 서버 구성

| 서버 | 포트 | 역할 | 주요 DB |
|------|------|------|---------|
| `Back/FastAPI/main.py` | **8001** | ML 추천·차트·재무·스크리너·게시판·마켓 레이더 | DuckDB + SQLite + Redis(캐시) |
| `Back/db/server.py` | **8000** | 회원 인증·뉴스 랭킹·내부 데이터 적재 | PostgreSQL + DuckDB(뉴스) + Redis(세션) |

---

## FastAPI 추천 서버 API 목록 (`/api/v1`)

| 라우터 | 엔드포인트 | 설명 |
|--------|-----------|------|
| stocks | `GET /stocks/recommendations` | 날짜·섹터·점수 필터 종목 추천 |
| stocks | `GET /stocks/search` | 티커·회사명 검색 |
| stocks | `GET /stocks/{ticker}/history` | 종목별 ML 점수 이력 |
| stocks | `GET /stocks/sectors/summary` | 섹터별 평균 점수 요약 |
| chart | `GET /chart/{ticker}` | OHLCV + 이동평균(5/20/60/120) |
| finance | `GET /finance/{ticker}` | 분기별 재무 지표 이력 |
| finance | `GET /finance/{ticker}/latest` | 최신 분기 재무 요약 |
| screener | `GET /screener` | ML점수 + PER/PBR/ROE 복합 스크리너 |
| compare | `GET /compare` | 2~10개 종목 점수이력·재무 비교 |
| portfolio | `GET /portfolio/backtest/summary` | v7·v8 백테스트 성과 요약 |
| portfolio | `GET /portfolio/backtest/monthly` | v8 Walk-Forward 월별 수익률 |
| board | `GET/POST /board/posts` | 종목 토론 게시글 CRUD |
| board | `GET/POST /board/comments` | 댓글 작성·조회 |
| board | `POST /board/posts/{id}/like` | 좋아요 토글 |
| market | `GET /market/regime` | 마켓 레이더 (Tier A 비율 → 국면 판단) |

---

## 인증·뉴스 서버 API 목록

| 라우터 | 엔드포인트 | 설명 |
|--------|-----------|------|
| auth | `POST /auth/check-email` | 이메일 중복 확인 + 인증번호 발송 |
| auth | `POST /auth/verify-code` | 인증번호 확인 |
| auth | `POST /auth/register` | 회원가입 |
| auth | `POST /auth/login` | 로그인 (Redis 세션 발급) |
| auth | `POST /auth/reset-password` | 비밀번호 변경 |
| news | `GET /news/list` | 날짜·카테고리 기반 뉴스 랭킹 조회 |
| internal | `POST /internal/ingest` | Go 파이프라인 뉴스 배치 적재 |

---

## 실행 방법

### 1. 프론트엔드

```bash
cd Front
npm install
npm run dev
# http://localhost:5173
```

### 2. FastAPI 추천 서버

```bash
cd Back/FastAPI
pip install -r requirements.txt
# DuckDB 사전 계산 (최초 1회)
python -m Back.MachineLearning.precompute_scores --model-version v8
python -m Back.MachineLearning.precompute_finance
python -m Back.MachineLearning.precompute_chart
# 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
# Swagger UI: http://localhost:8001/docs
```

### 3. 인증·뉴스 서버

```bash
cd Back/db
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 뉴스 파이프라인 (Go)

```bash
cd Back/go/go-news-kospi200-pipeline
cp configs/.env.example configs/.env   # 환경변수 설정
go run ./cmd/collector/main.go
```

---

## 주요 기술 스택

| 영역 | 기술 |
|------|------|
| 프론트엔드 | Vue 3, TypeScript, Vite, Pinia, Vue Router, Axios |
| 추천 API | FastAPI, DuckDB, Redis, Pydantic v2 |
| 인증 API | FastAPI, SQLAlchemy, PostgreSQL, bcrypt, Redis |
| ML 모델 | LightGBM, XGBoost, CatBoost (v7 앙상블 / v8 Walk-Forward) |
| 뉴스 파이프라인 | Go, Redis Stream, FinBERT(Python), DuckDB |

---

## 참고 문서

- [`백엔드_API_비즈니스로직_보고서.md`](./백엔드_API_비즈니스로직_보고서.md) — API 상세 명세 및 비즈니스 로직
- [`Back/go/go-news-kospi200-pipeline/docs/`](./Back/go/go-news-kospi200-pipeline/docs/) — 뉴스 파이프라인 설계 문서
