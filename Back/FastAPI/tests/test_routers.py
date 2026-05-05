"""
FastAPI ML 서버(:8001) 라우터 smoke test.

목적:
  - 라우터 등록/임포트 회귀 방지 (`/api/v1/...` 경로가 OpenAPI schema 에 있는지)
  - DB 데이터가 없어도 합리적 status code (200/404/503) 만 반환하는지

DuckDB 데이터가 없는 환경에서도 통과하도록 503/404 도 OK 로 간주한다.
"""

from __future__ import annotations

import pytest


# ── 헬스체크 / 루트 ──────────────────────────────────────────────────────────

def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "duckdb_exists" in body
    assert "duckdb_path" in body


def test_health_metrics(client):
    """드리프트 모니터링 엔드포인트 — DB 가 없어도 status='no-data' 로 200 반환."""
    r = client.get("/health/metrics?window_days=7")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"ok", "no-data", "error"}
    assert "metrics" in body
    if body["status"] == "ok":
        assert isinstance(body["metrics"], list)
        assert "summary" in body


# ── OpenAPI schema 회귀 ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "expected_path",
    [
        "/api/v1/stocks/recommendations",
        "/api/v1/stocks/search",
        "/api/v1/stocks/sectors/summary",
        "/api/v1/stocks/{ticker}/history",
        "/api/v1/chart/{ticker}",
        "/api/v1/finance/{ticker}",
        "/api/v1/screener",
        "/api/v1/compare",
        "/api/v1/portfolio/backtest/summary",
        "/api/v1/market/regime",
    ],
)
def test_openapi_has_route(client, expected_path):
    schema = client.get("/openapi.json").json()
    assert expected_path in schema["paths"], f"{expected_path} 가 OpenAPI 에 없음"


def test_openapi_no_unified_routes(client):
    """8001 에 board/news/users 라우터가 등록되지 않아야 한다 (8000 과 책임 분리)."""
    schema = client.get("/openapi.json").json()
    paths = schema["paths"].keys()
    assert not any(p.startswith("/api/v1/board") for p in paths)
    assert not any(p.startswith("/news") for p in paths)
    assert not any(p.startswith("/users") for p in paths)


# ── 데이터 의존 엔드포인트 — 200/404/503 모두 허용 (smoke level) ─────────────

OK_OR_DATA_MISSING = {200, 404, 503}


def test_recommendations(client):
    r = client.get("/api/v1/stocks/recommendations?top_k=5")
    assert r.status_code in OK_OR_DATA_MISSING


def test_versions(client):
    r = client.get("/api/v1/stocks/versions")
    assert r.status_code in OK_OR_DATA_MISSING
    if r.status_code == 200:
        body = r.json()
        assert isinstance(body.get("versions"), list)


def test_sectors_summary(client):
    r = client.get("/api/v1/stocks/sectors/summary")
    assert r.status_code in OK_OR_DATA_MISSING


def test_chart(client):
    r = client.get("/api/v1/chart/000660?period=1m")
    assert r.status_code in OK_OR_DATA_MISSING


def test_screener(client):
    r = client.get("/api/v1/screener?limit=5")
    assert r.status_code in OK_OR_DATA_MISSING


def test_compare(client):
    r = client.get("/api/v1/compare?tickers=005930,000660")
    assert r.status_code in OK_OR_DATA_MISSING


def test_market_regime(client):
    r = client.get("/api/v1/market/regime")
    assert r.status_code in OK_OR_DATA_MISSING


# ── CORS preflight ───────────────────────────────────────────────────────────

def test_cors_localhost_5173_allowed(client):
    r = client.options(
        "/api/v1/stocks/recommendations",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI CORS 미들웨어는 200 또는 204 로 응답
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_unknown_origin_blocked(client):
    r = client.options(
        "/api/v1/stocks/recommendations",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # 와일드카드 제거 후에는 허용 헤더가 응답에 포함되지 않아야 함
    assert r.headers.get("access-control-allow-origin") != "*"
    assert r.headers.get("access-control-allow-origin") != "https://evil.example.com"
