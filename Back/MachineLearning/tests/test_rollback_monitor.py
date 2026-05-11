"""
test_rollback_monitor.py
========================
차차기 W6D — rollback_monitor 단위 테스트.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data_pipeline"))
from rollback_monitor import (
    DEFAULT_THRESHOLD,
    RollbackDecision,
    check_rollback,
    emit_rollback_alert,
    evaluate_rollback,
    fetch_recent_statuses,
)


# ── evaluate_rollback (순수) ───────────────────────────────────────────────

def test_three_failures_triggers():
    d = evaluate_rollback(["failed", "failed", "failed"], step="x")
    assert d.trigger is True
    assert "3 consecutive failures" in d.reason


def test_mixed_does_not_trigger():
    d = evaluate_rollback(["failed", "ok", "failed"], step="x")
    assert d.trigger is False
    assert "need all 'failed'" in d.reason


def test_two_failures_below_threshold():
    d = evaluate_rollback(["failed", "failed"], step="x", threshold=3)
    assert d.trigger is False
    assert "insufficient completed runs" in d.reason


def test_empty_history():
    d = evaluate_rollback([], step="x")
    assert d.trigger is False


def test_custom_threshold():
    d = evaluate_rollback(["failed"] * 5, step="x", threshold=5)
    assert d.trigger is True


def test_default_threshold_is_3():
    assert DEFAULT_THRESHOLD == 3


def test_most_recent_first_semantics():
    """caller 가 최신 우선 정렬 — 마지막 3 행이 failed 면 trigger."""
    # 가장 최근 5 행 = [failed, failed, failed, ok, ok] (caller 가 LIMIT 5 DESC)
    # threshold=3 → 최근 3 = [failed, failed, failed] → trigger.
    d = evaluate_rollback(["failed", "failed", "failed", "ok", "ok"], step="x", threshold=3)
    assert d.trigger is True


# ── fetch_recent_statuses (DuckDB) ─────────────────────────────────────────

def _seed_cron_runs(db: Path, step: str, statuses: list[str]) -> None:
    """statuses 순서 = 오래된 순. test 가 최신 정렬 확인."""
    con = duckdb.connect(str(db))
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS cron_runs (
                run_id VARCHAR PRIMARY KEY,
                step VARCHAR NOT NULL,
                started_at TIMESTAMP NOT NULL,
                ended_at TIMESTAMP, status VARCHAR NOT NULL,
                error_class VARCHAR, error_message VARCHAR,
                rows_affected INTEGER, duration_sec REAL
            )
        """)
        from datetime import datetime, timedelta
        base = datetime(2026, 5, 1)
        for i, s in enumerate(statuses):
            con.execute(
                "INSERT INTO cron_runs (run_id, step, started_at, status) "
                "VALUES (?, ?, ?, ?)",
                [f"{step}_r{i}", step, base + timedelta(hours=i), s],
            )
    finally:
        con.close()


def test_fetch_filters_running_and_no_change(tmp_path):
    db = tmp_path / "t.duckdb"
    _seed_cron_runs(db, "s1",
                    ["ok", "failed", "no_change", "running", "failed", "failed"])
    out = fetch_recent_statuses(db, "s1", limit=3)
    # running·no_change 제외 후 최신 우선: [failed, failed, failed]
    assert out == ["failed", "failed", "failed"]


def test_fetch_returns_latest_first(tmp_path):
    db = tmp_path / "t.duckdb"
    _seed_cron_runs(db, "s1", ["ok", "ok", "failed"])
    out = fetch_recent_statuses(db, "s1", limit=10)
    assert out == ["failed", "ok", "ok"]


def test_fetch_step_isolation(tmp_path):
    """다른 step 의 실패는 영향 X."""
    db = tmp_path / "t.duckdb"
    _seed_cron_runs(db, "s1", ["ok", "ok"])
    _seed_cron_runs(db, "s2", ["failed", "failed", "failed"])
    out_s1 = fetch_recent_statuses(db, "s1", limit=3)
    out_s2 = fetch_recent_statuses(db, "s2", limit=3)
    assert out_s1 == ["ok", "ok"]
    assert out_s2 == ["failed", "failed", "failed"]


def test_fetch_db_missing_returns_empty(tmp_path):
    out = fetch_recent_statuses(tmp_path / "no_such.duckdb", "x", limit=3)
    assert out == []


# ── check_rollback (편의) ───────────────────────────────────────────────────

def test_check_rollback_integrates_fetch_and_evaluate(tmp_path):
    db = tmp_path / "t.duckdb"
    _seed_cron_runs(db, "s1", ["ok", "failed", "failed", "failed"])
    d = check_rollback("s1", duckdb_path=db)
    assert d.trigger is True


def test_check_rollback_step_isolation(tmp_path):
    db = tmp_path / "t.duckdb"
    _seed_cron_runs(db, "s1", ["failed", "failed", "failed"])
    _seed_cron_runs(db, "s2", ["ok", "ok", "ok"])
    assert check_rollback("s1", duckdb_path=db).trigger is True
    assert check_rollback("s2", duckdb_path=db).trigger is False


# ── emit_rollback_alert ─────────────────────────────────────────────────────

def test_emit_writes_sentinel_with_recovery_steps(tmp_path):
    decision = RollbackDecision(
        step="precompute_scores_a_prime",
        threshold=3,
        recent_statuses=("failed", "failed", "failed"),
        trigger=True,
        reason="3 consecutive failures",
    )
    path = emit_rollback_alert(
        decision, log_dir=tmp_path, duckdb_path=tmp_path / "no.duckdb",
        current_default="v11a_prime",
    )
    assert path.exists()
    body = path.read_text(encoding="utf-8")
    assert "step=precompute_scores_a_prime" in body
    assert "threshold=3" in body
    assert "current_default_model=v11a_prime" in body
    assert "복귀 절차" in body
    # 로그 append 확인.
    log = (tmp_path / "cron_status.log").read_text(encoding="utf-8")
    assert "ROLLBACK_ALERT" in log
    assert "precompute_scores_a_prime" in log


def test_emit_inserts_rollback_event_when_db_exists(tmp_path):
    db = tmp_path / "t.duckdb"
    # 빈 DB 미리 생성 (emit 이 ensure_table).
    duckdb.connect(str(db)).close()
    decision = RollbackDecision(
        step="x", threshold=3,
        recent_statuses=("failed",) * 3,
        trigger=True, reason="3 consecutive failures",
    )
    emit_rollback_alert(decision, log_dir=tmp_path, duckdb_path=db)
    con = duckdb.connect(str(db), read_only=True)
    try:
        rows = con.execute(
            "SELECT step, threshold, reason, resolved_at FROM rollback_events"
        ).fetchall()
    finally:
        con.close()
    assert len(rows) == 1
    assert rows[0][0] == "x"
    assert rows[0][1] == 3
    assert "3 consecutive" in rows[0][2]
    assert rows[0][3] is None    # 미해결


def test_emit_no_sentinel_for_non_trigger():
    """convenience — caller 가 trigger=False 일 때 emit 안 부르는 게 정상이지만,
    호출되면 어떻게 동작하는지 명시 — body 에 trigger 정보 그대로 박제."""
    # 본 모듈은 trigger=False 일 때도 sentinel 생성 — caller 가 책임지고 분기.
    # (별 단위 미작성 — 사용 패턴은 cron 에서 trigger=True 일 때만 호출)
    pass
