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
from .routers import stocks, portfolio


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
        print(f"[OK] DuckDB 연결: {DUCKDB_PATH}")
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
