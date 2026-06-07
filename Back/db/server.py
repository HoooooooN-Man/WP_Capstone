"""
파일 위치: Back/db/server.py
변경 이력:
  - HEAD: slowapi rate limiter (Tier 1B 4.4) + watchlist/cohort/events 라우터
  - origin/main 신규 머지: lifespan(APScheduler 매일 09:30 KST webnews 분석) + webnews 라우터 + 소셜 로그인 라우터
"""

import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

from api.auth.auth import router as auth_router
from api.auth.social import router as social_router
from api.news.newsranking import router as news_router
from api.news.webnews import router as webnews_router          # ← 신규 (origin/main)
from api.board.board import router as board_router
from api.users.users import router as users_router
from api.users.watchlist import router as watchlist_router
from api.users.cohort    import router as cohort_router
from api.events.events import router as events_router
from scheduler.webnews_worker import run_analysis              # ← 신규 (origin/main)

load_dotenv()

# ── 로깅 ──────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

# Tier 1B 4.4 (PRD §1.7): brute-force·스팸 방지 rate limiter.
# 클라이언트 IP 기준. 운영 환경에서는 X-Forwarded-For 등 신뢰 헤더 정책을 별도 결정.
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


# ── CORS ──────────────────────────────────────────────────────────────────────
def _parse_origins(env_value: str | None) -> list[str]:
    if not env_value:
        return []
    return [o.strip() for o in env_value.split(",") if o.strip()]

_DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
ALLOWED_ORIGINS = _parse_origins(os.getenv("CORS_ALLOW_ORIGINS")) or _DEFAULT_DEV_ORIGINS

# ── 스케줄러 (webnews 일일 분석) ──────────────────────────────────────────────
_scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 ─────────────────────────────────────────────
    _scheduler.add_job(
        run_analysis,
        CronTrigger(hour=9, minute=30, timezone="Asia/Seoul"),
        id="webnews_daily_analysis",
        replace_existing=True,
    )
    _scheduler.start()
    logging.getLogger("webnews_worker").info(
        "[SCHEDULER] 등록 완료 — 매일 09:30 KST 자동 분석"
    )
    yield
    # 서버 종료 시 ─────────────────────────────────────────────
    _scheduler.shutdown(wait=False)

# ── 앱 ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Stock Analysis System", lifespan=lifespan)

# Rate limiter 등록 — slowapi 는 app.state.limiter 를 통해 데코레이터와 연결.
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """rate limit 초과 시 통일 에러 스키마로 응답 (PRD §1.3 호환)."""
    return JSONResponse(
        status_code=429,
        content={
            "code":       "RATE_LIMITED",
            "message":    f"요청이 너무 많습니다. 잠시 후 다시 시도해 주세요. (limit: {exc.detail})",
            "request_id": request.headers.get("X-Request-ID", ""),
        },
        headers={"Retry-After": "60"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# ── 라우터 등록 ───────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(social_router)     # ← 신규 (origin/main, Google/Kakao/Naver)
app.include_router(news_router)
app.include_router(webnews_router)    # ← 신규 (origin/main)
app.include_router(board_router)
app.include_router(users_router)
app.include_router(watchlist_router)  # Tier 1.6 — /users/me/watchlist CRUD
app.include_router(cohort_router)     # W2C — /users/me/cohort GET·PUT
app.include_router(events_router)     # W1B — /events impressions·clicks·outcomes


# ── Stub endpoints (Front_v2 미구현 endpoint 401/404 회피) ──────────────────
# 비로그인 (인증 헤더 없음) → 401 대신 빈 응답 200 으로 frontend graceful 처리.
# 로그인 후엔 별도 라우터가 우선 매칭됨 (FastAPI 첫 매칭 라우터 우선).
from fastapi import APIRouter as _Stub
_stub = _Stub(tags=["stub"])

@_stub.get("/users/me", summary="내 프로필 — stub (미구현)")
def _stub_me():
    return {"nickname": None, "email": None, "cohort": None, "is_advice": False}

@_stub.get("/users/me/notes", summary="투자노트 — stub")
def _stub_notes():
    return {"total": 0, "items": []}

@_stub.get("/users/me/portfolio/holdings", summary="보유종목 — stub")
def _stub_holdings():
    return {"items": []}

@_stub.get("/users/me/portfolio/cohort/{cohort}", summary="코호트 포트폴리오 — stub")
def _stub_cohort_portfolio(cohort: str):
    return {"cohort": cohort, "total": 0, "items": [],
            "summary": {"n_picks": 0, "n_valid_returns": 0, "avg_return_pct": None,
                        "best_pick": None, "worst_pick": None, "win_rate_pct": None}}

@_stub.get("/users/me/portfolio/cohort/{cohort}/preview", summary="코호트 preview — stub")
def _stub_cohort_preview(cohort: str):
    return {"cohort": cohort, "n_picks": 0, "picks": [], "is_advice": False}

app.include_router(_stub)


@app.get("/")
def root():
    return {"message": "Server is running"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
