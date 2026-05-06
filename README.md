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
| `Back/FastAPI/main.py` | **8001** | ML 추천·차트·재무·스크리너·비교·포트폴리오·마켓 레이더 (READ-ONLY) | DuckDB(market_data) + Redis(응답 캐시) |
| `Back/db/server.py`    | **8000** | 회원 인증·게시판·뉴스(피드/랭킹)·알림·내부 적재 (OLTP)         | PostgreSQL + DuckDB(news_data, 쓰기 전용 분리) + Redis(세션) |

> 두 DuckDB 파일은 **물리적으로 분리**되어 lock 충돌이 없다.
> `DUCKDB_PATH` (시장·스코어·재무, read-only) ↔ `NEWS_DUCKDB_PATH` (뉴스 적재).

---

## FastAPI ML 서버 API 목록 (`:8001/api/v1`)

| 라우터 | 엔드포인트 | 설명 |
|--------|-----------|------|
| stocks    | `GET /stocks/recommendations`        | 날짜·섹터·점수 필터 종목 추천 |
| stocks    | `GET /stocks/search`                 | 티커·회사명 검색 |
| stocks    | `GET /stocks/{ticker}/history`       | 종목별 ML 점수 이력 |
| stocks    | `GET /stocks/sectors/summary`        | 섹터별 평균 점수 요약 |
| chart     | `GET /chart/{ticker}`                | OHLCV + 이동평균(5/20/60/120) |
| finance   | `GET /finance/{ticker}`              | 분기별 재무 지표 이력 |
| finance   | `GET /finance/{ticker}/latest`       | 최신 분기 재무 요약 |
| screener  | `GET /screener`                      | ML점수 + PER/PBR/ROE 복합 스크리너 |
| compare   | `GET /compare`                       | 2~10개 종목 점수이력·재무 비교 |
| portfolio | `GET /portfolio/backtest/summary`    | v7·v8 백테스트 성과 요약 |
| portfolio | `GET /portfolio/backtest/monthly`    | v8 Walk-Forward 월별 수익률 |
| market    | `GET /market/regime`                 | 마켓 레이더 (Tier A 비율 → 국면 판단) |

---

## 인증·커뮤니티·뉴스 서버 API 목록 (`:8000`)

| 라우터 | 엔드포인트 | 설명 |
|--------|-----------|------|
| auth      | `POST /auth/check-email`                   | 이메일 중복 확인 + 인증번호 발송 |
| auth      | `POST /auth/verify-code`                   | 인증번호 확인 |
| auth      | `POST /auth/register`                      | 회원가입 |
| auth      | `POST /auth/login`                         | 로그인 (Redis 세션 발급) |
| auth      | `POST /auth/reset-password`                | 비밀번호 변경 (로그인 상태) |
| auth      | `POST /auth/reset-password-via-email`      | 비밀번호 변경 (이메일 인증) |
| users     | `GET  /users/notifications`                | 내 알림 목록 |
| users     | `POST /users/notifications/read-all`       | 모든 알림 읽음 처리 |
| users     | `GET  /users/{nickname}/public`            | 공개 프로필 조회 |
| board     | `GET /api/v1/board/popular`                | 인기 게시글 |
| board     | `GET /api/v1/board/posts?ticker=...`       | 게시글 목록 (페이지네이션) |
| board     | `GET /api/v1/board/posts/detail/{post_id}` | 게시글 상세 (조회수 +1) |
| board     | `POST /api/v1/board/posts`                 | 게시글 작성 (인증 필수) |
| board     | `DELETE /api/v1/board/posts/{post_id}`     | 게시글 삭제 (작성자 본인) |
| board     | `POST /api/v1/board/comments`              | 댓글 작성 |
| board     | `POST /api/v1/board/posts/{post_id}/like`  | 좋아요 토글 |
| news      | `GET /api/v1/news/feed`                    | 최신 뉴스 피드 (감성 라벨) |
| news      | `GET /api/v1/news/detail/{news_id}`        | 뉴스 단건 상세 |
| news      | `GET /api/v1/news/rankings`                | 날짜·카테고리 뉴스 랭킹 |
| news      | `GET /api/v1/news/rankings/dates`          | 랭킹 데이터 보유 날짜 |
| news      | `GET /api/v1/news/rankings/{news_id}`      | 랭킹 항목 상세 |
| internal  | `POST /internal/ingest`                    | Go 파이프라인 뉴스 배치 적재 |

---

## 실행 방법

### 1. 프론트엔드

```bash
cd Front
# Vite 8 + Tailwind v4 + vite-plugin-pwa 의 peerDependencies 가
# 일부 비호환 메타데이터를 가지므로 --legacy-peer-deps 권장.
npm install --legacy-peer-deps
npm run dev
# http://localhost:5173
```

> 주요 빌드 의존성은 모두 안정 릴리스(`vue-router 5.0.x` / `vite 8.0.x`)이며,
> `package.json` 은 `~` 범위로 패치 업데이트만 허용하도록 잠가두었다.
> 환경변수는 `Front/.env.example` 참조 (`VITE_API_BASE_ML`, `VITE_API_BASE_AUTH`).

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
