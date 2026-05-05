"""
pytest fixtures for FastAPI ML 서버 (8001).

핵심 설계:
  - TestClient 는 FastAPI 앱을 직접 import 하므로 서버를 띄울 필요 없음.
  - DuckDB 가 없는 CI 환경에서도 통과하도록, lifespan 의 `init_duckdb` 가
    실패해도 앱 자체는 기동되어야 한다 (현재 구현이 이미 그렇게 됨).
  - 일부 엔드포인트는 데이터 의존성이 강해 503/404 가 정상 응답일 수 있다.
    smoke test 는 "프로세스 크래시 없이 합리적 status code 반환" 만 확인.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 루트 경로를 sys.path 에 추가하여 `Back.FastAPI.main` import 가능하게 함
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture(scope="session")
def app():
    """FastAPI 앱 객체 (lifespan 은 TestClient 가 자동 처리)."""
    # 임포트 시점에 환경 의존성 (DUCKDB_PATH 등) 체크가 일어나지 않도록 lazy 임포트.
    from Back.FastAPI.main import app as _app
    return _app


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
