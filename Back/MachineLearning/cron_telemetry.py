"""
cron_telemetry.py
=================
M#35 — cron / 배치 작업 진입·종료 시점을 DuckDB `cron_runs` 에 기록.

cron_runs 스키마 (이미 존재):
  run_id       VARCHAR  PK    UUID
  step         VARCHAR        job 이름 (예: 'dart_finance_backfill_q3')
  started_at   TIMESTAMP      진입 시각 (NOW)
  ended_at     TIMESTAMP      종료 시각 (NULL = 아직 실행 중)
  status       VARCHAR        ok / failed / no_change / running
  error_class  VARCHAR        실패 시 Exception class name
  error_message VARCHAR       실패 시 메시지 (200자 절단)
  rows_affected INTEGER       작업이 처리한 행수 (선택)
  duration_sec FLOAT          ended_at - started_at

사용:
    from cron_telemetry import track_run

    with track_run("dart_finance_q3") as run:
        n = do_backfill()
        run.rows = n   # 선택

    # 또는 수동:
    run_id = mark_start("my_job")
    try:
        ...
        mark_end(run_id, "ok", rows_affected=42)
    except Exception as e:
        mark_end(run_id, "failed", error=e)
        raise
"""
from __future__ import annotations

import contextlib
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import duckdb

# DUCKDB_PATH — env 우선, 없으면 운영 기본 경로.
_DEFAULT_DUCKDB = Path(r"E:\Capstone Data\project_data\db\market_data.duckdb")
DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", str(_DEFAULT_DUCKDB)))


def _connect() -> duckdb.DuckDBPyConnection:
    """Write-mode 연결. 실패 시 None 대신 raise — 텔레메트리 실패는 명확하게."""
    if not DUCKDB_PATH.exists():
        raise FileNotFoundError(f"cron_telemetry: DuckDB 부재 {DUCKDB_PATH}")
    return duckdb.connect(str(DUCKDB_PATH), read_only=False)


def _ensure_table(con: duckdb.DuckDBPyConnection) -> None:
    """cron_runs 가 없으면 생성 (idempotent)."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS cron_runs (
            run_id         VARCHAR PRIMARY KEY,
            step           VARCHAR NOT NULL,
            started_at     TIMESTAMP NOT NULL,
            ended_at       TIMESTAMP,
            status         VARCHAR NOT NULL,
            error_class    VARCHAR,
            error_message  VARCHAR,
            rows_affected  INTEGER,
            duration_sec   FLOAT
        )
    """)


def mark_start(step: str) -> str:
    """job 진입 시점 INSERT. 반환된 run_id 를 mark_end 에 넘긴다."""
    run_id = str(uuid.uuid4())
    try:
        con = _connect()
        _ensure_table(con)
        con.execute(
            "INSERT INTO cron_runs (run_id, step, started_at, status) "
            "VALUES (?, ?, CURRENT_TIMESTAMP, 'running')",
            [run_id, step],
        )
        con.close()
    except Exception:
        # 텔레메트리 실패가 본 작업을 막으면 안 됨 — 조용히 통과.
        # (DUCKDB write lock 충돌 등 — 별도 알람 hook 권장)
        pass
    return run_id


def mark_end(
    run_id: str,
    status: str = "ok",
    *,
    rows_affected: Optional[int] = None,
    error: Optional[BaseException] = None,
) -> None:
    """job 종료 시점 UPDATE — status, duration, rows_affected, error 정보 박제."""
    err_class = err_msg = None
    if error is not None:
        err_class = type(error).__name__
        err_msg = str(error)[:200]
    try:
        con = _connect()
        _ensure_table(con)
        con.execute(
            """
            UPDATE cron_runs
               SET ended_at      = CURRENT_TIMESTAMP,
                   status        = ?,
                   error_class   = ?,
                   error_message = ?,
                   rows_affected = ?,
                   duration_sec  = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at))
             WHERE run_id = ?
            """,
            [status, err_class, err_msg, rows_affected, run_id],
        )
        con.close()
    except Exception:
        pass


class _RunHandle:
    """track_run 컨텍스트 안에서 외부가 채울 수 있는 변경 가능 핸들."""
    __slots__ = ("rows",)
    def __init__(self) -> None:
        self.rows: Optional[int] = None


@contextlib.contextmanager
def track_run(step: str):
    """컨텍스트 매니저 사용 패턴.

    `with track_run("job_name") as h:` 형식. h.rows 에 처리 행수 set 시 자동 기록.
    예외 발생 시 status='failed' + 예외 정보 박제 후 re-raise.
    """
    run_id = mark_start(step)
    handle = _RunHandle()
    t0 = time.time()
    try:
        yield handle
    except BaseException as e:
        mark_end(run_id, "failed", error=e, rows_affected=handle.rows)
        raise
    else:
        # rows 가 0 이면 'no_change' 로 표기 — 의미 있는 신호 (스킵 vs 진짜 OK).
        status = "no_change" if handle.rows == 0 else "ok"
        mark_end(run_id, status, rows_affected=handle.rows)
    finally:
        # duration 은 mark_end 가 DB 측 EXTRACT 로 정확히 기록.
        # 여기서는 디버그용 출력만 (선택적으로 비활성 가능).
        if os.getenv("CRON_TELEMETRY_VERBOSE"):
            print(f"[cron] {step}: {time.time() - t0:.2f}s")
