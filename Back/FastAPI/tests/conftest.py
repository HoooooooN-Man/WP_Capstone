"""
conftest.py
===========
pytest fixtures — FastAPI TestClient + 공용 헬퍼.

원칙:
  - 외부 IO (DuckDB / Redis) 없이는 동작 못 하는 통합 테스트 위주.
  - 외부 의존성 (Redis, 8000 PG) 부재 시 자동 skip — CI 환경에서도 깨지지 않게.
  - DUCKDB_PATH 는 환경 그대로 사용 (운영 DB 직접). 변경하려면 env 로 override.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Back/ 를 sys.path 추가 — `from FastAPI.main import app` 가능하도록.
_BACK_DIR = Path(__file__).resolve().parents[2]
if str(_BACK_DIR) not in sys.path:
    sys.path.insert(0, str(_BACK_DIR))


@pytest.fixture(scope="session")
def app():
    """FastAPI app instance — lifespan(init_duckdb 워밍업) 실행 보장."""
    from FastAPI.main import app as fastapi_app
    return fastapi_app


@pytest.fixture()
def client(app):
    """TestClient (httpx WSGI 어댑터) — 단일 요청 단위."""
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def have_duckdb() -> bool:
    """DuckDB 파일이 존재하는지 — 없으면 통합 테스트 skip."""
    from FastAPI.core.config import DUCKDB_PATH
    return DUCKDB_PATH.exists()


@pytest.fixture(scope="session")
def have_archive() -> bool:
    """transparency/playground 가 의존하는 _archive 디렉토리 존재 여부."""
    from FastAPI.core.config import CAPSTONE_ROOT
    base = Path(CAPSTONE_ROOT).parent / "_archive"
    return base.exists()
