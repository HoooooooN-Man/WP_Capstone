"""
cron_runtime.py
===============
차차기 W6B — cron 실행 공통 인프라 (실패 알림 + 추적).

설계 (사용자 권고 — 외부 의존 없음, 3 채널 동시):
  1. logs/cron_status.log : 모든 run 한 줄 append (시작·종료·실패).
  2. logs/FAIL_<step>_<timestamp>.flag : 실패 시 sentinel 파일 (사용자 디렉토리 모니터링).
  3. DuckDB `cron_runs` 테이블 : 구조화 적재 (W2 대시보드·W6D roll-back trigger 입력).

핵심 API:
    from cron_runtime import cron_run
    with cron_run("collect_and_build") as ctx:
        ...
        ctx.report_rows(187_810)   # 선택 — 적재 row 수

  성공: status='ok', ended_at·duration 자동.
  실패: status='failed', error_class·error_message 기록 + sentinel 생성 + 예외 재발생.

cron_runs schema:
    run_id        VARCHAR PRIMARY KEY (uuid)
    step          VARCHAR
    started_at    TIMESTAMP
    ended_at      TIMESTAMP NULL
    status        VARCHAR  -- 'running' | 'ok' | 'failed'
    error_class   VARCHAR NULL
    error_message VARCHAR NULL
    rows_affected INTEGER NULL
    duration_sec  REAL NULL

W6D (roll-back 자동 트리거) 는 본 테이블의 *최근 N runs* 가 'failed' 면 트리거.
"""

from __future__ import annotations

import os
import traceback
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional


DEFAULT_LOG_DIR = Path(
    os.getenv("CRON_LOG_DIR", str(Path(__file__).resolve().parents[3] / "logs"))
)
DEFAULT_DUCKDB = Path(os.getenv(
    "DUCKDB_PATH",
    r"E:\Capstone Data\project_data\db\market_data.duckdb",
))


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cron_runs (
    run_id        VARCHAR PRIMARY KEY,
    step          VARCHAR NOT NULL,
    started_at    TIMESTAMP NOT NULL,
    ended_at      TIMESTAMP,
    status        VARCHAR NOT NULL,
    error_class   VARCHAR,
    error_message VARCHAR,
    rows_affected INTEGER,
    duration_sec  REAL
)
"""


@dataclass
class CronContext:
    step:        str
    run_id:      str
    started_at:  datetime
    log_dir:     Path
    duckdb_path: Optional[Path]
    rows_affected: Optional[int] = None
    _status:     str = "running"
    _error:      Optional[BaseException] = None

    def report_rows(self, n: int) -> None:
        self.rows_affected = int(n)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _append_log(self, msg: str) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        line = f"{self._now().isoformat(timespec='seconds')}\t{self.step}\t{self.run_id[:8]}\t{msg}\n"
        with open(self.log_dir / "cron_status.log", "a", encoding="utf-8") as f:
            f.write(line)

    def _write_sentinel(self, error_class: str) -> Path:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        ts = self._now().strftime("%Y%m%d_%H%M%S")
        path = self.log_dir / f"FAIL_{self.step}_{ts}.flag"
        body = (
            f"step={self.step}\n"
            f"run_id={self.run_id}\n"
            f"started_at={self.started_at.isoformat(timespec='seconds')}\n"
            f"failed_at={self._now().isoformat(timespec='seconds')}\n"
            f"error_class={error_class}\n"
            f"error_message={(str(self._error) if self._error else '')[:1000]}\n"
        )
        path.write_text(body, encoding="utf-8")
        return path

    # ── DuckDB INSERT/UPDATE ────────────────────────────────────────────

    def _ensure_table(self, con) -> None:
        con.execute(CREATE_TABLE_SQL)

    def _db_insert_start(self) -> None:
        if self.duckdb_path is None:
            return
        try:
            import duckdb
            con = duckdb.connect(str(self.duckdb_path))
            try:
                self._ensure_table(con)
                con.execute(
                    "INSERT INTO cron_runs (run_id, step, started_at, status) "
                    "VALUES (?, ?, ?, 'running')",
                    [self.run_id, self.step, self.started_at],
                )
            finally:
                con.close()
        except Exception:
            # DB 실패는 cron 자체를 막지 않음 — log·sentinel 로 보충.
            pass

    def _db_update_end(self) -> None:
        if self.duckdb_path is None:
            return
        try:
            import duckdb
            end = self._now()
            duration = (end - self.started_at).total_seconds()
            err_class = type(self._error).__name__ if self._error else None
            err_msg   = (str(self._error)[:1000] if self._error else None)
            con = duckdb.connect(str(self.duckdb_path))
            try:
                self._ensure_table(con)
                con.execute(
                    """UPDATE cron_runs SET
                          ended_at      = ?,
                          status        = ?,
                          error_class   = ?,
                          error_message = ?,
                          rows_affected = ?,
                          duration_sec  = ?
                       WHERE run_id = ?""",
                    [end, self._status, err_class, err_msg,
                     self.rows_affected, duration, self.run_id],
                )
            finally:
                con.close()
        except Exception:
            pass

    # ── 상태 전이 ──────────────────────────────────────────────────────

    def mark_success(self) -> None:
        self._status = "ok"
        self._append_log(f"OK rows={self.rows_affected if self.rows_affected is not None else ''}")
        self._db_update_end()

    def mark_no_change(self, reason: str = "") -> None:
        """변화 없음 — cron 살아있는 신호 + 불필요한 적재 회피 (W6C 권고).
        sentinel 생성 안 함. status='no_change'. 호출 후 context exit 시 mark_success
        가 *덮어쓰지 않음* (context manager 가 status != 'running' 확인)."""
        self._status = "no_change"
        suffix = f" reason={reason}" if reason else ""
        self._append_log(f"NO_CHANGE{suffix}")
        self._db_update_end()

    def mark_failure(self, exc: BaseException) -> None:
        self._status = "failed"
        self._error  = exc
        err_class = type(exc).__name__
        self._append_log(f"FAIL {err_class}: {str(exc)[:200]}")
        sentinel = self._write_sentinel(err_class)
        self._append_log(f"sentinel written: {sentinel.name}")
        self._db_update_end()


# ── public context manager ─────────────────────────────────────────────

@contextmanager
def cron_run(
    step:        str,
    *,
    log_dir:     Path | str | None = None,
    duckdb_path: Path | str | None = None,
) -> Iterator[CronContext]:
    """
    cron 실행 wrapper. 시작·종료·실패 자동 기록.

    Parameters
    ----------
    step        : 실행 단계 이름 ("collect_and_build" 등). cron_runs.step 컬럼.
    log_dir     : sentinel·status.log 위치. None → CRON_LOG_DIR env 또는 default.
    duckdb_path : cron_runs 적재 DB. None → 적재 skip (테스트·드라이런 용).
    """
    ld = Path(log_dir) if log_dir is not None else DEFAULT_LOG_DIR
    dp: Optional[Path]
    if duckdb_path is False:    # type: ignore[comparison-overlap]
        dp = None
    elif duckdb_path is None:
        dp = DEFAULT_DUCKDB if DEFAULT_DUCKDB.exists() else None
    else:
        dp = Path(duckdb_path)

    ctx = CronContext(
        step=step,
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc),
        log_dir=ld,
        duckdb_path=dp,
    )
    ctx._append_log("START")
    ctx._db_insert_start()
    try:
        yield ctx
    except BaseException as e:
        ctx.mark_failure(e)
        raise
    else:
        # 명시적 상태 전이 (mark_no_change 등) 가 있었으면 그대로 유지.
        # 'running' 인 경우만 자동 success.
        if ctx._status == "running":
            ctx.mark_success()
