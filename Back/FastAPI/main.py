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

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import APP_TITLE, APP_VERSION, API_PREFIX, DUCKDB_PATH
from .routers import stocks, portfolio, chart, finance, screener, compare, market, board, news, users_stub
from .services.data import init_duckdb
from .services.board_db import init_board_db


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

    # SQLite 게시판 DB 초기화 (로그인 없는 간단 게시판)
    try:
        init_board_db()
        print("[OK] SQLite 게시판 DB 초기화 완료")
    except Exception as e:
        print(f"[WARNING] 게시판 DB 초기화 실패: {e}")
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 배포 시 허용 도메인으로 교체
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록 (API 버전 prefix)
app.include_router(stocks.router,    prefix=API_PREFIX)
app.include_router(portfolio.router, prefix=API_PREFIX)
app.include_router(market.router,    prefix=API_PREFIX)
app.include_router(chart.router,     prefix=API_PREFIX)
app.include_router(finance.router,   prefix=API_PREFIX)
app.include_router(screener.router,  prefix=API_PREFIX)
app.include_router(compare.router,   prefix=API_PREFIX)
app.include_router(board.router,     prefix=API_PREFIX)
# 뉴스 / 사용자 stub은 dbapi.js (no /api/v1 prefix) 호환을 위해 prefix 없이 등록
app.include_router(news.router)
app.include_router(users_stub.router)


# ── 헬스체크 ───────────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
def root():
    return {
        "status": "ok",
        "app": APP_TITLE,
        "version": APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health():
    return {
        "status": "ok",
        "duckdb_exists": DUCKDB_PATH.exists(),
        "duckdb_path": str(DUCKDB_PATH),
    }
