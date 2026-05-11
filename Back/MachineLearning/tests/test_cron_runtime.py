"""
test_cron_runtime.py
====================
차차기 W6B — cron_runtime context manager 단위 테스트.
DuckDB 는 tmp file, log·sentinel 은 tmp dir. 외부 의존 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data_pipeline"))
from cron_runtime import CREATE_TABLE_SQL, CronContext, cron_run


# ── 성공 경로 ──────────────────────────────────────────────────────────────

def test_success_writes_log_and_no_sentinel(tmp_path):
    with cron_run("step_x", log_dir=tmp_path, duckdb_path=False):
        pass
    log = (tmp_path / "cron_status.log").read_text(encoding="utf-8")
    assert "START" in log
    assert "OK"    in log
    sentinels = list(tmp_path.glob("FAIL_*.flag"))
    assert sentinels == []


def test_report_rows_appears_in_log(tmp_path):
    with cron_run("step_x", log_dir=tmp_path, duckdb_path=False) as ctx:
        ctx.report_rows(187_810)
    log = (tmp_path / "cron_status.log").read_text(encoding="utf-8")
    assert "rows=187810" in log


def test_success_writes_duckdb(tmp_path):
    db = tmp_path / "t.duckdb"
    with cron_run("step_x", log_dir=tmp_path, duckdb_path=db) as ctx:
        ctx.report_rows(42)
    con = duckdb.connect(str(db), read_only=True)
    try:
        rows = con.execute(
            "SELECT step, status, rows_affected FROM cron_runs"
        ).fetchall()
    finally:
        con.close()
    assert len(rows) == 1
    assert rows[0] == ("step_x", "ok", 42)


def test_success_duration_recorded(tmp_path):
    db = tmp_path / "t.duckdb"
    with cron_run("step_x", log_dir=tmp_path, duckdb_path=db):
        pass
    con = duckdb.connect(str(db), read_only=True)
    try:
        dur = con.execute("SELECT duration_sec FROM cron_runs").fetchone()[0]
    finally:
        con.close()
    assert dur is not None
    assert dur >= 0


# ── 실패 경로 ──────────────────────────────────────────────────────────────

def test_failure_writes_sentinel_and_log(tmp_path):
    with pytest.raises(ValueError):
        with cron_run("step_fail", log_dir=tmp_path, duckdb_path=False):
            raise ValueError("boom 한글 — em-dash")
    log = (tmp_path / "cron_status.log").read_text(encoding="utf-8")
    assert "FAIL ValueError" in log
    assert "boom" in log
    sentinels = list(tmp_path.glob("FAIL_step_fail_*.flag"))
    assert len(sentinels) == 1
    body = sentinels[0].read_text(encoding="utf-8")
    assert "step=step_fail" in body
    assert "error_class=ValueError" in body
    assert "boom" in body


def test_failure_writes_duckdb_failed_status(tmp_path):
    db = tmp_path / "t.duckdb"
    with pytest.raises(RuntimeError):
        with cron_run("step_fail", log_dir=tmp_path, duckdb_path=db):
            raise RuntimeError("nope")
    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute(
            "SELECT status, error_class, error_message FROM cron_runs"
        ).fetchone()
    finally:
        con.close()
    assert row[0] == "failed"
    assert row[1] == "RuntimeError"
    assert "nope" in row[2]


def test_failure_propagates_original_exception_type(tmp_path):
    """예외 swallow 안 함 — Task Scheduler 가 returncode != 0 으로 인지 가능."""
    class MyErr(Exception):
        pass
    with pytest.raises(MyErr):
        with cron_run("x", log_dir=tmp_path, duckdb_path=False):
            raise MyErr("custom")


# ── 재진입 (동시 실행) ─────────────────────────────────────────────────────

def test_concurrent_runs_have_unique_ids(tmp_path):
    db = tmp_path / "t.duckdb"
    with cron_run("a", log_dir=tmp_path, duckdb_path=db) as c1:
        with cron_run("b", log_dir=tmp_path, duckdb_path=db) as c2:
            assert c1.run_id != c2.run_id
    con = duckdb.connect(str(db), read_only=True)
    try:
        n = con.execute("SELECT COUNT(*) FROM cron_runs").fetchone()[0]
    finally:
        con.close()
    assert n == 2


# ── DB 부재·실패 시 graceful ────────────────────────────────────────────

def test_db_path_missing_does_not_crash(tmp_path):
    """duckdb_path 가 존재하지 않으면 cron 자체는 성공 (log·sentinel 만)."""
    nonexistent = tmp_path / "no_such.duckdb"
    # 첫 실행 시 file 이 생성됨 (duckdb.connect 가 만듦). 즉 fail 안 함.
    with cron_run("x", log_dir=tmp_path, duckdb_path=nonexistent):
        pass
    # cron 자체 성공 — 로그 OK 라인 있어야.
    log = (tmp_path / "cron_status.log").read_text(encoding="utf-8")
    assert "OK" in log


def test_duckdb_path_false_skips_db(tmp_path):
    """duckdb_path=False — DB 적재 skip, 로그·sentinel 만."""
    with cron_run("x", log_dir=tmp_path, duckdb_path=False):
        pass
    log = (tmp_path / "cron_status.log").read_text(encoding="utf-8")
    assert "OK" in log


# ── schema 검증 ────────────────────────────────────────────────────────────

def test_create_table_sql_contains_required_columns():
    required = {"run_id", "step", "started_at", "ended_at", "status",
                "error_class", "error_message", "rows_affected", "duration_sec"}
    for col in required:
        assert col in CREATE_TABLE_SQL, f"{col} missing in cron_runs schema"


# ── W6C — no_change 상태 ───────────────────────────────────────────────────

def test_no_change_status_no_sentinel(tmp_path):
    """mark_no_change → sentinel 미생성, 로그 NO_CHANGE 라인."""
    db = tmp_path / "t.duckdb"
    with cron_run("step_nc", log_dir=tmp_path, duckdb_path=db) as ctx:
        ctx.mark_no_change("data unchanged")
    log = (tmp_path / "cron_status.log").read_text(encoding="utf-8")
    assert "NO_CHANGE" in log
    assert "data unchanged" in log
    assert not list(tmp_path.glob("FAIL_*.flag"))
    con = duckdb.connect(str(db), read_only=True)
    try:
        status = con.execute("SELECT status FROM cron_runs").fetchone()[0]
    finally:
        con.close()
    assert status == "no_change"


def test_no_change_not_overwritten_by_auto_success(tmp_path):
    """mark_no_change 호출 후 context exit 정상 종료 → mark_success 가 덮어쓰지 않음."""
    db = tmp_path / "t.duckdb"
    with cron_run("step_nc", log_dir=tmp_path, duckdb_path=db) as ctx:
        ctx.mark_no_change()
    con = duckdb.connect(str(db), read_only=True)
    try:
        status = con.execute("SELECT status FROM cron_runs").fetchone()[0]
    finally:
        con.close()
    assert status == "no_change"   # 'ok' 로 덮어쓰지 않음


def test_explicit_success_still_works(tmp_path):
    """변화 있는 정상 run — context 가 자동 mark_success 호출 (기존 동작)."""
    db = tmp_path / "t.duckdb"
    with cron_run("step_ok", log_dir=tmp_path, duckdb_path=db):
        pass
    con = duckdb.connect(str(db), read_only=True)
    try:
        status = con.execute("SELECT status FROM cron_runs").fetchone()[0]
    finally:
        con.close()
    assert status == "ok"


def test_no_change_then_failure(tmp_path):
    """no_change 상태에서 예외 → failure 가 덮어씀 (예외 우선)."""
    db = tmp_path / "t.duckdb"
    with pytest.raises(RuntimeError):
        with cron_run("step_x", log_dir=tmp_path, duckdb_path=db) as ctx:
            ctx.mark_no_change("hmm")
            raise RuntimeError("then crashed")
    con = duckdb.connect(str(db), read_only=True)
    try:
        row = con.execute(
            "SELECT status, error_class FROM cron_runs"
        ).fetchone()
    finally:
        con.close()
    assert row == ("failed", "RuntimeError")
    # 실패 sentinel 도 생성됨.
    assert list(tmp_path.glob("FAIL_step_x_*.flag"))
