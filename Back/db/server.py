"""
파일 위치: Back/db/server.py
기존 server.py 에서 변경된 부분:
  1. lifespan 추가 (APScheduler 매일 09:30 KST 등록)
  2. FastAPI(lifespan=lifespan) 으로 변경
  3. webnews_router 등록
  4. logging 기본 설정 추가
"""

import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.auth.auth import router as auth_router
from api.auth.social import router as social_router
from api.news.newsranking import router as news_router
from api.news.webnews import router as webnews_router          # ← 추가
from api.board.board import router as board_router
from api.users.users import router as users_router
from scheduler.webnews_worker import run_analysis              # ← 추가

load_dotenv()

# ── 로깅 ──────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

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

# ── 스케줄러 ──────────────────────────────────────────────────────────────────
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
app = FastAPI(title="Stock Analysis System", lifespan=lifespan)  # ← lifespan 추가

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# ── 라우터 등록 ───────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(news_router)
app.include_router(webnews_router)    # ← 추가
app.include_router(board_router)
app.include_router(users_router)
app.include_router(social_router)


@app.get("/")
def root():
    return {"message": "Server is running"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
