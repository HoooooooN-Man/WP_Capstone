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

import logging
import os
import sys

# ── UTF-8 모드 강제 ───────────────────────────────────────────────────────────
# 한국어 Windows(cp949 로캘)에서 시스템 Python 이 UTF-8 모드 없이 실행되면
# DuckDB VARCHAR(한글 종목명 등)가 깨져 들어온다. uvicorn 으로 기동됐는데
# utf8_mode 가 꺼져 있으면 `-X utf8` 로 자기 자신을 한 번 재실행한다.
# (pytest 등 다른 진입점에서는 sys.argv[0] 에 'uvicorn' 이 없어 재실행 안 됨)
if (
    not sys.flags.utf8_mode
    and os.environ.get("_WP_UTF8_REEXEC") != "1"
    and "uvicorn" in (sys.argv[0] or "").lower()
):
    os.environ["_WP_UTF8_REEXEC"] = "1"
    os.execv(
        sys.executable,
        [sys.executable, "-X", "utf8", "-m", "uvicorn", *sys.argv[1:]],
    )

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .core.config import APP_TITLE, APP_VERSION, API_PREFIX, DUCKDB_PATH
from .core.errors import register_exception_handlers
from .core.middleware import RequestIDMiddleware
# 8001 = ML 분석 서버. 게시판/뉴스/사용자/인증은 8000 (Back/db/server.py) 가 담당.
# (board/news/users_stub 코드 파일은 보관하되 본 서버에서는 등록하지 않음.)
from .routers import stocks, portfolio, chart, finance, screener, compare, market, realtime, transparency, playground, winners, admin, cohort_backtest
from .schemas.health import (
    RootResponse,
    HealthResponse,
    MetricsResponse,
    SystemStatusResponse,
    ModelVersionInfo,
)
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
_CORS_ENV = os.getenv("CORS_ALLOW_ORIGINS")
ALLOWED_ORIGINS = _parse_origins(_CORS_ENV) or _DEFAULT_DEV_ORIGINS
if not _CORS_ENV:
    # 운영 배포에서 .env 가 누락된 채 띄우면 dev origin (localhost:5173 등) 만 허용되어
    # 실 프론트가 차단됨 — 호출 차단의 원인이 모호하므로 시작 시점에 명확히 경고.
    logging.getLogger(__name__).warning(
        "[CORS] CORS_ALLOW_ORIGINS 환경변수 미설정 — dev 폴백(%s) 사용. "
        "운영 배포 시 반드시 도메인 화이트리스트로 .env 에 명시하세요.",
        ",".join(_DEFAULT_DEV_ORIGINS),
    )


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

# Host 헤더 검증 — 운영 reverse proxy 뒤에서 Host 헤더 spoof 차단.
# ALLOWED_HOSTS 환경변수가 없으면 dev 폴백 (* — 모든 호스트 허용).
_ALLOWED_HOSTS_ENV = os.getenv("ALLOWED_HOSTS")
_ALLOWED_HOSTS = (
    [h.strip() for h in _ALLOWED_HOSTS_ENV.split(",") if h.strip()]
    if _ALLOWED_HOSTS_ENV
    else ["*"]
)
if _ALLOWED_HOSTS == ["*"]:
    logging.getLogger(__name__).warning(
        "[host] ALLOWED_HOSTS 미설정 — 모든 Host 허용(개발용). "
        "운영에서는 ALLOWED_HOSTS=api.example.com 처럼 명시."
    )
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_ALLOWED_HOSTS)

# CORS — 화이트리스트 기반. 운영 시 CORS_ALLOW_ORIGINS 환경변수로 도메인 명시.
# H#26: allow_headers 를 "*" 에서 명시 리스트로 좁힘. credentials=True 와 "*" 조합은
# CORS 사양상 거의 모든 요청 헤더 허용 — XSS 발생 시 임의 헤더 주입 면적이 큼.
_ALLOWED_HEADERS = [
    "Accept", "Accept-Language", "Content-Type", "Content-Language",
    "Origin", "Authorization",
    "session-token",        # 헤더 기반 인증 (legacy 호환)
    "X-Request-ID",
    "X-CSRF-Token",         # 쿠키 기반 인증 시 CSRF 토큰
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=_ALLOWED_HEADERS,
    expose_headers=["X-Request-ID"],
)

# Request-ID 부여 — 가장 외층에 둔다 (Starlette: 나중에 추가된 미들웨어가 외층).
# 모든 응답에 X-Request-ID 헤더가 부착되며, 에러 응답은 이 id 를 본문에도 포함.
app.add_middleware(RequestIDMiddleware)

# 통합 에러 응답 스키마 (PRD §1.3 / Tier 1.7).
register_exception_handlers(app)

# 라우터 등록 (ML 분석 도메인만)
app.include_router(stocks.router,    prefix=API_PREFIX)
app.include_router(portfolio.router, prefix=API_PREFIX)
app.include_router(market.router,    prefix=API_PREFIX)
app.include_router(chart.router,     prefix=API_PREFIX)
app.include_router(finance.router,   prefix=API_PREFIX)
app.include_router(winners.router,   prefix=API_PREFIX)
app.include_router(screener.router,  prefix=API_PREFIX)
app.include_router(compare.router,   prefix=API_PREFIX)
app.include_router(transparency.router, prefix=API_PREFIX)  # Tier 1.5 — holdout 박제 read-only
app.include_router(playground.router,   prefix=API_PREFIX)  # Tier 2.5 — 정책 grid playground
app.include_router(admin.router,        prefix=API_PREFIX)  # M#35 — cron_runs 텔레메트리 조회
app.include_router(cohort_backtest.router, prefix=API_PREFIX)  # 19_cohort_variants — 백테 성과 노출

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


@app.get("/system/status", response_model=SystemStatusResponse, tags=["health"])
def system_status():
    """
    프론트 상태 페이지·모니터링용 통합 헬스 정보.

    - DuckDB 파일 존재 여부 + 절대 경로
    - Redis 가용성 (캐시 ON/OFF 추정)
    - scores 테이블에 적재된 모든 model_version + 각각의 최신 거래일·적재 시각·행수
    - `resolve_version("latest")` 가 현재 가리키는 운영 default

    P0-11 — 신규 프론트의 "오늘 데이터는 언제 적재됐는가?" 위젯에 직접 사용.
    """
    from .services._core import (
        con as _con,
        get_redis as _get_redis,
        resolve_version as _resolve_version,
        DEFAULT_MODEL_VERSION_ENV,
    )

    if not DUCKDB_PATH.exists():
        return SystemStatusResponse(
            status="no-data",
            app=APP_TITLE,
            version=APP_VERSION,
            duckdb_exists=False,
            duckdb_path=str(DUCKDB_PATH),
            redis_available=False,
            error="scores.duckdb 파일이 존재하지 않습니다.",
        )

    try:
        rows = _con().execute(
            """
            SELECT
                model_version,
                COUNT(*) AS row_count,
                MAX(CAST(date AS VARCHAR)) AS latest_date,
                MAX(inserted_at) AS inserted_at
            FROM scores
            GROUP BY model_version
            ORDER BY MAX(inserted_at) DESC NULLS LAST
            """
        ).fetchall()
    except Exception as e:
        # 내부 SQL/예외 메시지는 클라이언트에 노출하지 않는다 (CRITICAL #4 와 동일 원칙).
        # 운영자는 서버 로그에서 traceback 확인.
        logging.getLogger(__name__).exception("[/system/status] scores query failed")
        del e
        return SystemStatusResponse(
            status="error",
            app=APP_TITLE,
            version=APP_VERSION,
            duckdb_exists=True,
            duckdb_path=str(DUCKDB_PATH),
            redis_available=False,
            error="scores 조회 실패 — 서버 로그를 확인하세요.",
        )

    models = [
        ModelVersionInfo(
            model_version=r[0],
            row_count=int(r[1] or 0),
            latest_date=r[2],
            inserted_at=r[3],
        )
        for r in rows
    ]

    default_model: str | None = None
    default_latest: str | None = None
    try:
        default_model = _resolve_version("latest")
        for m in models:
            if m.model_version == default_model:
                default_latest = m.latest_date
                break
    except Exception:
        default_model = None

    redis_available = _get_redis() is not None

    return SystemStatusResponse(
        status="ok",
        app=APP_TITLE,
        version=APP_VERSION,
        duckdb_exists=True,
        duckdb_path=str(DUCKDB_PATH),
        redis_available=redis_available,
        default_model=default_model,
        default_model_env=os.getenv(DEFAULT_MODEL_VERSION_ENV) or None,
        models=models,
        scores_latest_date=default_latest,
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
    except Exception:
        # 내부 예외 메시지 노출 차단 — 운영자는 logger.exception 으로 추적.
        logging.getLogger(__name__).exception("[/health/metrics] failed")
        return MetricsResponse(
            status="error",
            error="metrics 조회 실패 — 서버 로그를 확인하세요.",
            metrics=[],
        )
