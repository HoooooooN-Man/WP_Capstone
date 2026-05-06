"""
core/config.py
==============
경로·환경 설정 상수.
환경변수(또는 .env)로 오버라이드 가능 — 코드 변경 없이 배포 환경을 바꿀 수 있도록 설계.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 이 파일(config.py) 기준으로 .env 경로를 명시 — uvicorn 실행 위치에 무관하게 로드됨
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=True)

# ── 루트 경로 ─────────────────────────────────────────────────────────────────
# Back/FastAPI/core/config.py → Back/FastAPI/ → Back/ → WP_Capstone/ → Capstone Data/
_FASTAPI_DIR  = Path(__file__).resolve().parent.parent   # Back/FastAPI/
_BACK_DIR     = _FASTAPI_DIR.parent                      # Back/
_REPO_DIR     = _BACK_DIR.parent                         # WP_Capstone/

CAPSTONE_ROOT: Path = Path(os.getenv("CAPSTONE_ROOT", str(_REPO_DIR.parent)))
MODELS_DIR:    Path = CAPSTONE_ROOT / "models"
SEED_CSV:      Path = CAPSTONE_ROOT / "preprocessing" / "seed.csv"

# ── DuckDB ───────────────────────────────────────────────────────────────────
# 시장/스코어/재무 DuckDB (read-only). 동일 파일을 다른 프로세스가 쓰면 lock 충돌.
DUCKDB_PATH: Path = Path(os.getenv("DUCKDB_PATH", str(_FASTAPI_DIR / "scores.duckdb")))

# 뉴스 적재 전용 DuckDB. db 서버(8000)의 /internal/ingest 가 쓰고, 본 서버는 읽기만.
# 반드시 DUCKDB_PATH 와 다른 파일을 가리켜야 한다.
_DEFAULT_NEWS_DB = _BACK_DIR / "db" / "db" / "news_data.duckdb"
NEWS_DUCKDB_PATH: Path = Path(os.getenv("NEWS_DUCKDB_PATH", str(_DEFAULT_NEWS_DB)))

# ── SQLite (게시판 OLTP) ─────────────────────────────────────────────────────
BOARD_DB_PATH: Path = Path(os.getenv("BOARD_DB_PATH", str(_FASTAPI_DIR / "board.db")))

# ── Redis ────────────────────────────────────────────────────────────────────
# 8001 ML 서버의 응답 캐시는 redis-queue 인스턴스의 db=1 을 사용한다.
# 비밀번호는 충돌 방지를 위해 REDIS_QUEUE_PASSWORD 를 우선 읽고, 없으면 REDIS_PASSWORD.
REDIS_HOST:     str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT:     int = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB:       int = int(os.getenv("REDIS_DB", "1"))       # db=0 은 인증 서버가 사용
REDIS_PASSWORD: str | None = (
    os.getenv("REDIS_QUEUE_PASSWORD")
    or os.getenv("REDIS_PASSWORD")
    or None
)
REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "60"))  # 초

# ── 원천 데이터 CSV ──────────────────────────────────────────────────────────
STOCK_DATA_CSV:       Path = CAPSTONE_ROOT / "data" / "stock_data_clean.csv"
FINANCE_CSV:          Path = CAPSTONE_ROOT / "preprocessing" / "financial_indicators_clean.csv"

# ── 백테스트 결과 파일 ────────────────────────────────────────────────────────
# v9 S3: prob 상위 150 + Regime Filter + 유동성 + 섹터캡 25%
WF_MONTHLY_RETURNS_CSV: Path = Path(os.getenv(
    "WF_MONTHLY_RETURNS_CSV",
    str(MODELS_DIR / "v9_s3" / "results" / "wf_portfolio_monthly_returns.csv"),
))
WF_PERFORMANCE_TXT: Path = Path(os.getenv(
    "WF_PERFORMANCE_TXT",
    str(MODELS_DIR / "v9_s3" / "results" / "wf_performance_summary.txt"),
))
V7_COMPARISON_CSV: Path = MODELS_DIR / "backtest_comparison" / "comparison_summary.csv"

# ── 앱 설정 ───────────────────────────────────────────────────────────────────
APP_TITLE:   str = "Stock Recommendation API"
APP_VERSION: str = "1.0.0"
API_PREFIX:  str = "/api/v1"
