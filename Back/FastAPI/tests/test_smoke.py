"""스모크 — root/health/system_status 와 핵심 라우터의 happy path."""
import pytest


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_system_status_no_str_exc_leak(client):
    """CRITICAL #4 회귀 가드 — error 필드에 raw exception 노출 금지."""
    r = client.get("/system/status")
    assert r.status_code == 200
    body = r.json()
    err = body.get("error")
    if err:
        for forbidden in ("Traceback", "Timeout connecting", "psycopg2", "redis."):
            assert forbidden not in err, f"내부 예외 노출: {err}"


def test_recommendations_top3(client, have_duckdb):
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/stocks/recommendations?top_k=3")
    assert r.status_code == 200
    body = r.json()
    items = body.get("items", [])
    assert len(items) <= 3
    if items:
        assert "ticker" in items[0]
        # H#17 가드: cumulative_return_pct 부착 회귀 방지 — None 이라도 키 자체는 있어야.
        assert "cumulative_return_pct" in items[0]


def test_radar_nonexistent_ticker_no_500(client, have_duckdb):
    """CRITICAL #7 회귀 — 미존재 ticker 에 NameError 500 금지."""
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/stocks/999999/radar")
    assert r.status_code in (200, 404), r.text


def test_compare_invalid_ticker_422(client, have_duckdb):
    """MEDIUM #43 회귀 — 비숫자 ticker 는 422."""
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/compare?tickers=abc,def&period=3m")
    assert r.status_code == 422


def test_screener_invalid_tier_422(client, have_duckdb):
    """MEDIUM #30 회귀 — tier=X 같은 부정값은 422."""
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/screener?tier=X")
    assert r.status_code == 422


def test_dividend_years_paid_not_always_zero(client, have_duckdb):
    """CRITICAL #8 회귀 — years_paid 가 항상 0 이면 안 됨 (배당 종목 한정)."""
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/stocks/005930/dividend")
    assert r.status_code == 200
    body = r.json()
    # 삼성은 11년 연속 배당 — years_paid >= 5 보장 가드
    assert body.get("years_paid") is not None
    assert body.get("years_paid", 0) >= 5, f"years_paid={body.get('years_paid')}"


def test_outcome_days_since_rec_not_null(client, have_duckdb):
    """CRITICAL #9 회귀 — days_since_rec 가 모두 null 이면 안 됨."""
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/stocks/058970/outcome")
    if r.status_code == 200:
        body = r.json()
        # outcome 자체가 None 인 경우 (A 티어 아님) 는 통과, 있으면 days_since_rec 필수
        if body:
            assert body.get("days_since_rec") is not None
