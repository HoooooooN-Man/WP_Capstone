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

load_dotenv()  # Back/FastAPI/.env 가 있으면 읽어들임

# ── 루트 경로 ─────────────────────────────────────────────────────────────────
# Back/FastAPI/core/config.py → Back/FastAPI/ → Back/ → WP_Capstone/ → Capstone Data/
_FASTAPI_DIR  = Path(__file__).resolve().parent.parent   # Back/FastAPI/
_BACK_DIR     = _FASTAPI_DIR.parent                      # Back/
_REPO_DIR     = _BACK_DIR.parent                         # WP_Capstone/

CAPSTONE_ROOT: Path = Path(os.getenv("CAPSTONE_ROOT", str(_REPO_DIR.parent)))
MODELS_DIR:    Path = CAPSTONE_ROOT / "models"
SEED_CSV:      Path = CAPSTONE_ROOT / "preprocessing" / "seed.csv"

# ── DuckDB ───────────────────────────────────────────────────────────────────
DUCKDB_PATH: Path = Path(os.getenv("DUCKDB_PATH", str(_FASTAPI_DIR / "scores.duckdb")))

# ── SQLite (게시판 OLTP) ─────────────────────────────────────────────────────
BOARD_DB_PATH: Path = Path(os.getenv("BOARD_DB_PATH", str(_FASTAPI_DIR / "board.db")))

# ── Redis ────────────────────────────────────────────────────────────────────
REDIS_HOST:     str = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT:     int = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB:       int = int(os.getenv("REDIS_DB", "1"))       # db=0 은 인증 서버가 사용
REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "60"))  # 초

# ── 원천 데이터 CSV ──────────────────────────────────────────────────────────
STOCK_DATA_CSV:       Path = CAPSTONE_ROOT / "data" / "stock_data_clean.csv"
FINANCE_CSV:          Path = CAPSTONE_ROOT / "preprocessing" / "financial_indicators_clean.csv"

# ── 백테스트 결과 파일 ────────────────────────────────────────────────────────
WF_MONTHLY_RETURNS_CSV: Path = MODELS_DIR / "v8_walk_forward" / "results" / "wf_portfolio_monthly_returns.csv"
WF_PERFORMANCE_TXT:     Path = MODELS_DIR / "v8_walk_forward" / "results" / "wf_performance_summary.txt"
V7_COMPARISON_CSV:      Path = MODELS_DIR / "backtest_comparison" / "comparison_summary.csv"

# ── 앱 설정 ───────────────────────────────────────────────────────────────────
APP_TITLE:   str = "Stock Recommendation API"
APP_VERSION: str = "1.0.0"
API_PREFIX:  str = "/api/v1"
