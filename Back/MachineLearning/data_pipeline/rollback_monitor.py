"""
rollback_monitor.py
===================
차차기 W6D — cron_runs 최근 N 연속 실패 → DEFAULT_MODEL_VERSION roll-back 알림.

설계 결정 (사용자 권고):
  1. **트리거**: 같은 step 의 *최근 N=3 연속 status='failed'*. no_change·running 제외.
     다른 step 의 실패는 별개 trigger (예: precompute_scores 실패는 모델 roll-back,
     data_collect 실패는 데이터 정지 알림 — 둘은 다른 처리).
  2. **자동 swap 안 함**. 환경변수 외부 변경 불가 + 실패 원인 미해결 상태 자동 복귀
     위험. 대안: sentinel + 로그 + DB 기록 → 사용자가 보고 manual 복귀.
  3. **복귀**: 자동 조건 없음. 사용자가 실패 원인 점검 후 DEFAULT_MODEL_VERSION env
     수정 + ROLLBACK sentinel manual 삭제.

본 모듈은 *순수 함수* (check_rollback) + DuckDB 어댑터 (emit_rollback_alert).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


DEFAULT_THRESHOLD = 3
DEFAULT_LOG_DIR = Path(
    os.getenv("CRON_LOG_DIR", str(Path(__file__).resolve().parents[3] / "logs"))
)
DEFAULT_DUCKDB = Path(os.getenv(
    "DUCKDB_PATH",
    r"E:\Capstone Data\project_data\db\market_data.duckdb",
))


@dataclass(frozen=True)
class RollbackDecision:
    step:        str
    threshold:   int
    recent_statuses: tuple[str, ...]    # 최근 N (없으면 빈)
    trigger:     bool
    reason:      str


# ── 순수 함수 ───────────────────────────────────────────────────────────────

def evaluate_rollback(
    recent_statuses: Iterable[str],
    *,
    step:      str,
    threshold: int = DEFAULT_THRESHOLD,
) -> RollbackDecision:
    """
    recent_statuses: 최근 N (또는 그 이하) 의 status 값.
                     *running·no_change 제외* 한 *완료 run* 만 caller 가 필터.
                     순서는 *최신 우선* (LIMIT N ORDER BY started_at DESC).
    """
    statuses = tuple(recent_statuses)
    if len(statuses) < threshold:
        return RollbackDecision(
            step=step, threshold=threshold, recent_statuses=statuses,
            trigger=False,
            reason=f"insufficient completed runs ({len(statuses)} < {threshold})",
        )
    last_n = statuses[:threshold]
    if all(s == "failed" for s in last_n):
        return RollbackDecision(
            step=step, threshold=threshold, recent_statuses=last_n,
            trigger=True,
            reason=f"{threshold} consecutive failures",
        )
    return RollbackDecision(
        step=step, threshold=threshold, recent_statuses=last_n,
        trigger=False,
        reason=f"recent {threshold}: {','.join(last_n)} (need all 'failed')",
    )


# ── DuckDB 어댑터 ──────────────────────────────────────────────────────────

CREATE_ROLLBACK_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rollback_events (
    event_id     VARCHAR PRIMARY KEY,
    step         VARCHAR NOT NULL,
    triggered_at TIMESTAMP NOT NULL,
    threshold    INTEGER  NOT NULL,
    reason       VARCHAR,
    resolved_at  TIMESTAMP,        -- 사용자 manual 표시 (NULL = 미해결)
    resolution_note VARCHAR
)
"""


def fetch_recent_statuses(
    duckdb_path: Path,
    step:        str,
    *,
    limit:       int = DEFAULT_THRESHOLD,
) -> list[str]:
    """cron_runs 에서 해당 step 의 *running·no_change 제외* 최근 N 행 status.
    최신 우선 정렬. DB·테이블 부재 → 빈 리스트 (보수적)."""
    if not duckdb_path.exists():
        return []
    try:
        import duckdb
        con = duckdb.connect(str(duckdb_path), read_only=True)
        try:
            rows = con.execute(
                """SELECT status FROM cron_runs
                   WHERE step = ? AND status NOT IN ('running', 'no_change')
                   ORDER BY started_at DESC
                   LIMIT ?""",
                [step, int(limit)],
            ).fetchall()
        finally:
            con.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def emit_rollback_alert(
    decision:    RollbackDecision,
    *,
    log_dir:     Path | str | None = None,
    duckdb_path: Path | str | None = None,
    current_default: Optional[str] = None,
    fallback_suggestion: Optional[str] = None,
) -> Path:
    """sentinel 생성 + 로그 append + rollback_events 적재. sentinel 경로 반환.

    *자동 env 변경 없음.* sentinel 본문에 복귀 절차 명시.
    """
    ld = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
    ld.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    ts  = now.strftime("%Y%m%d_%H%M%S")
    sentinel = ld / f"ROLLBACK_{decision.step}_{ts}.flag"

    current_default = current_default or os.getenv("DEFAULT_MODEL_VERSION", "<unset, latest=inserted_at>")
    body = (
        f"event=rollback_alert\n"
        f"step={decision.step}\n"
        f"triggered_at={now.isoformat(timespec='seconds')}\n"
        f"threshold={decision.threshold}\n"
        f"recent_statuses={','.join(decision.recent_statuses)}\n"
        f"reason={decision.reason}\n"
        f"current_default_model={current_default}\n"
        f"suggested_fallback={fallback_suggestion or '<scores 테이블에서 이전 안정 model_version 확인>'}\n"
        f"\n"
        f"## 복귀 절차 (manual — 자동 swap 안 함)\n"
        f"1. logs/cron_status.log 와 logs/FAIL_{decision.step}_*.flag 확인.\n"
        f"2. 실패 원인 점검 후 수정 (코드·데이터·환경).\n"
        f"3. 정상 1회 run 으로 cron_runs 에 status='ok' 추가.\n"
        f"4. (선택) DEFAULT_MODEL_VERSION env var 수정 — resolve_version 이 새 default 사용.\n"
        f"5. 본 sentinel manual 삭제 + rollback_events.resolved_at UPDATE.\n"
    )
    sentinel.write_text(body, encoding="utf-8")

    # 로그 append.
    with open(ld / "cron_status.log", "a", encoding="utf-8") as f:
        f.write(
            f"{now.isoformat(timespec='seconds')}\t{decision.step}\t"
            f"ROLLBACK_ALERT\t{decision.reason}\n"
        )

    # DB rollback_events 적재.
    dp = Path(duckdb_path) if duckdb_path else (DEFAULT_DUCKDB if DEFAULT_DUCKDB.exists() else None)
    if dp is not None and dp.exists():
        try:
            import duckdb, uuid
            con = duckdb.connect(str(dp))
            try:
                con.execute(CREATE_ROLLBACK_TABLE_SQL)
                con.execute(
                    """INSERT INTO rollback_events
                       (event_id, step, triggered_at, threshold, reason)
                       VALUES (?, ?, ?, ?, ?)""",
                    [str(uuid.uuid4()), decision.step, now,
                     decision.threshold, decision.reason],
                )
            finally:
                con.close()
        except Exception:
            pass    # DB 실패는 cron 자체를 막지 않음 — sentinel·로그가 1차.
    return sentinel


def check_rollback(
    step:        str,
    *,
    threshold:   int = DEFAULT_THRESHOLD,
    duckdb_path: Path | str | None = None,
) -> RollbackDecision:
    """편의 함수: fetch + evaluate. emit 은 caller 가 결정."""
    dp = Path(duckdb_path) if duckdb_path else DEFAULT_DUCKDB
    recent = fetch_recent_statuses(dp, step, limit=threshold)
    return evaluate_rollback(recent, step=step, threshold=threshold)
