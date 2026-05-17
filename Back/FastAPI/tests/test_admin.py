"""M#35 — admin/cron-runs 조회 + cron_telemetry 헬퍼 동작."""
import pytest


def test_cron_runs_list(client, have_duckdb):
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/admin/cron-runs?limit=10")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        body = r.json()
        assert "items" in body and "total" in body
        assert isinstance(body["items"], list)


def test_cron_runs_health(client, have_duckdb):
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    r = client.get("/api/v1/admin/cron-runs/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") in ("ok", "degraded", "stale", "unknown")
    assert "message" in body


def test_cron_runs_invalid_status_422(client):
    """status pattern 검증 — 부정 값은 422."""
    r = client.get("/api/v1/admin/cron-runs?status=XYZ")
    assert r.status_code == 422


def _can_write_duckdb() -> bool:
    """다른 프로세스(예: 운영 중인 8001)가 DuckDB write 락을 잡고 있는지 사전 점검.
    잡혀 있으면 cron_telemetry 가 silent fail 하므로 (운영 정책) 테스트를 skip.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "MachineLearning"))
    from cron_telemetry import DUCKDB_PATH
    import duckdb
    try:
        c = duckdb.connect(str(DUCKDB_PATH), read_only=False)
        c.close()
        return True
    except Exception:
        return False


def test_cron_telemetry_helper_records(have_duckdb):
    """track_run 컨텍스트가 cron_runs 에 행을 INSERT/UPDATE 하는지 직접 검증.

    8001 백엔드가 DuckDB write 락을 잡고 있으면 cron_telemetry 가 silent fail —
    그 경우 skip (운영 환경에서는 cron 작업이 백엔드와 시간대 분리됨).
    """
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    if not _can_write_duckdb():
        pytest.skip("DuckDB write lock — 8001 동시 가동 환경 (정책상 silent fail 이라 기록 안 됨)")
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "MachineLearning"))
    from cron_telemetry import track_run, DUCKDB_PATH
    import duckdb

    with track_run("__pytest_smoke__") as run:
        run.rows = 7

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    row = con.execute(
        "SELECT status, rows_affected FROM cron_runs WHERE step='__pytest_smoke__' ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    con.close()
    assert row is not None
    assert row[0] == "ok"
    assert row[1] == 7


def test_cron_telemetry_failure_path(have_duckdb):
    """예외 시 status='failed' + error_class 기록."""
    if not have_duckdb:
        pytest.skip("DuckDB unavailable")
    if not _can_write_duckdb():
        pytest.skip("DuckDB write lock — 8001 동시 가동 환경")
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "MachineLearning"))
    from cron_telemetry import track_run, DUCKDB_PATH
    import duckdb

    with pytest.raises(ValueError):
        with track_run("__pytest_smoke_fail__"):
            raise ValueError("intentional test failure")

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    row = con.execute(
        "SELECT status, error_class, error_message FROM cron_runs "
        "WHERE step='__pytest_smoke_fail__' ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    con.close()
    assert row is not None
    assert row[0] == "failed"
    assert row[1] == "ValueError"
    assert "intentional" in (row[2] or "")
