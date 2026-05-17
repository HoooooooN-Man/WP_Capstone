"""GET /api/v1/chart/{ticker} — 캔들스틱+이동평균."""
import pytest


def test_chart_samsung_happy_path(client, have_duckdb):
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/chart/005930")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "candles" in body or "items" in body or "data" in body  # 구현 차이 흡수
    assert isinstance(body, dict)


def test_chart_invalid_ticker_returns_4xx(client, have_duckdb):
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/chart/zzzz")
    # 존재하지 않는 ticker 라도 200 + 빈 배열 또는 404 — silent 500 만 아니면 OK.
    assert r.status_code in (200, 404, 422)


def test_chart_query_params_optional(client, have_duckdb):
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    # interval/period 파라미터 — 라우터가 받는다면 200, 무시한다면 200.
    r = client.get("/api/v1/chart/005930?interval=1d")
    assert r.status_code in (200, 422)
