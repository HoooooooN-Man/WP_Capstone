"""
main.py — Stock Recommendation API
====================================
실행:
    cd Back/FastAPI
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload

Swagger UI:  http://localhost:8001/docs
ReDoc:       http://localhost:8001/redoc
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import APP_TITLE, APP_VERSION, API_PREFIX, DUCKDB_PATH
from .core.errors import register_exception_handlers
from .core.middleware import RequestIDMiddleware
# 8001 = ML 분석 서버. 게시판/뉴스/사용자/인증은 8000 (Back/db/server.py) 가 담당.
# (board/news/users_stub 코드 파일은 보관하되 본 서버에서는 등록하지 않음.)
from .routers import stocks, portfolio, chart, finance, screener, compare, market, realtime, transparency, playground
from .schemas.health import RootResponse, HealthResponse, MetricsResponse
from .services.data import init_duckdb, get_model_metrics


def _parse_origins(env_value: str | None) -> list[str]:
    """CORS_ALLOW_ORIGINS 환경변수에서 콤마로 구분된 origin 리스트를 파싱."""
    if not env_value:
        return []
    return [o.strip() for o in env_value.split(",") if o.strip()]


# 기본 허용: 로컬 개발 (Vite 5173, Vite preview 4173).
# 운영에서는 CORS_ALLOW_ORIGINS=https://app.example.com,https://admin.example.com 처럼 명시.
_DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
ALLOWED_ORIGINS = _parse_origins(os.getenv("CORS_ALLOW_ORIGINS")) or _DEFAULT_DEV_ORIGINS


# ── 앱 수명 이벤트 ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 scores.duckdb 존재 여부 확인
    if not DUCKDB_PATH.exists():
        print(
            f"\n[WARNING] scores.duckdb 없음: {DUCKDB_PATH}\n"
            "  → Back/MachineLearning/precompute_scores.py --model-version v7 을 먼저 실행하세요.\n"
        )
    else:
        import asyncio
        # 스레드에서 실행하여 이벤트 루프 블로킹 방지
        await asyncio.get_event_loop().run_in_executor(None, init_duckdb)
        print(f"[OK] DuckDB 연결 + 워밍업 완료: {DUCKDB_PATH}")

        # 사용자 첫 페이지 진입 시 발생하는 cold 14초 회피 — 핵심 endpoint 미리 fetch.
        # 이 호출은 _cached() 를 거치므로 process-local memory cache 에 결과 저장 → 첫 호출 즉시 hit.
        def _warm_endpoints():
            try:
                from .services import data as svc
                svc.get_market_regime(model_version="latest")
                svc.get_recommendations(top_k=50)  # top_k=50 cohort 페이지용
                svc.get_recommendations(top_k=0)   # 전체
                svc.get_sector_summary(model_version="latest")
                print("[OK] API endpoint 워밍업 완료 (market_regime · recommendations · sector_summary)")
            except Exception as e:
                print(f"[WARN] API 워밍업 실패 (graceful): {e}")
        await asyncio.get_event_loop().run_in_executor(None, _warm_endpoints)

    yield


# ── FastAPI 앱 ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=(
        "주식 추천 API — v7 앙상블(LightGBM·XGBoost·CatBoost) 모델 기반 "
        "날짜별 백분위 점수(1~100)로 종목 투자 매력도를 수치화합니다.\n\n"
        "- `model_version=latest` → 가장 최근 적재된 모델 자동 선택\n"
        "- 새 모델 추가: `precompute_scores.py --model-version v8 ...` 만 실행"
    ),
    lifespan=lifespan,
)

# CORS — 화이트리스트 기반. 운영 시 CORS_ALLOW_ORIGINS 환경변수로 도메인 명시.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Request-ID 부여 — 가장 외층에 둔다 (Starlette: 나중에 추가된 미들웨어가 외층).
# 모든 응답에 X-Request-ID 헤더가 부착되며, 에러 응답은 이 id 를 본문에도 포함.
app.add_middleware(RequestIDMiddleware)

# 통합 에러 응답 스키마 (PRD §1.3 / Tier 1.7).
register_exception_handlers(app)

# 라우터 등록 (ML 분석 도메인만)
app.include_router(stocks.router,         prefix=API_PREFIX)
app.include_router(stocks.winners_router, prefix=API_PREFIX)  # /winners stub
app.include_router(portfolio.router, prefix=API_PREFIX)
app.include_router(market.router,    prefix=API_PREFIX)
app.include_router(chart.router,     prefix=API_PREFIX)
app.include_router(finance.router,   prefix=API_PREFIX)
app.include_router(screener.router,  prefix=API_PREFIX)
app.include_router(compare.router,   prefix=API_PREFIX)
app.include_router(transparency.router, prefix=API_PREFIX)  # Tier 1.5 — holdout 박제 read-only
app.include_router(playground.router,   prefix=API_PREFIX)  # Tier 2.5 — 정책 grid playground

# 실시간 시세 WebSocket (no /api/v1 prefix — wss:// 표준 경로)
app.include_router(realtime.router)


# ── 헬스체크 ───────────────────────────────────────────────────────────────────

@app.get("/", response_model=RootResponse, tags=["health"])
def root():
    return RootResponse(
        status="ok",
        app=APP_TITLE,
        version=APP_VERSION,
        docs="/docs",
    )


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health():
    return HealthResponse(
        status="ok",
        duckdb_exists=DUCKDB_PATH.exists(),
        duckdb_path=str(DUCKDB_PATH),
    )


@app.get("/health/metrics", response_model=MetricsResponse, tags=["health"])
def health_metrics(
    model_version: str = "latest",
    window_days: int = 30,
):
    """
    모델 점수 분포 모니터링 (드리프트 감지용).

    최근 `window_days` 일 동안의 일별 통계:
      - mean / median / stddev
      - quantiles (10/25/50/75/90)
      - tier 분포 (A/B/C/D 종목 수)
    분포가 급격히 달라지면 모델 drift 또는 데이터 파이프라인 이슈 가능.
    """
    if not DUCKDB_PATH.exists():
        return MetricsResponse(status="no-data", metrics=[])
    try:
        result = get_model_metrics(model_version=model_version, window_days=window_days)
        return MetricsResponse(status="ok", **result)
    except Exception as e:
        return MetricsResponse(status="error", error=str(e), metrics=[])
