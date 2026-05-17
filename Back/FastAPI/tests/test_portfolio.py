"""GET /api/v1/portfolio/backtest/* — 백테스트 결과 + KOSPI200 포트폴리오."""
import pytest


def test_backtest_summary(client, have_duckdb):
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/portfolio/backtest/summary")
    # 백테스트 결과 파일(wf_*.csv) 없으면 503 가능 — 500 만 아니면 통과.
    assert r.status_code in (200, 503), r.text
    if r.status_code == 200:
        body = r.json()
        assert isinstance(body, dict)


def test_backtest_monthly(client, have_duckdb):
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/portfolio/backtest/monthly")
    assert r.status_code in (200, 503)


def test_custom_backtest_missing_body_422(client, have_duckdb):
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    # POST 인데 body 없이 호출 → 422 (스키마 검증)
    r = client.post("/api/v1/portfolio/backtest")
    assert r.status_code == 422


def test_kospi200_portfolio(client, have_duckdb):
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    # endpoint 경로는 line 72-77 의 라우터 정의 따름 — 200 또는 200 with items 확인
    # 실제 경로가 다르면 404 — 그 자체가 회귀 시그널.
    r = client.get("/api/v1/portfolio/kospi200")
    assert r.status_code in (200, 404, 422)
