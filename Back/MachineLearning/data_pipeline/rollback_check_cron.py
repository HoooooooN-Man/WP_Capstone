"""
rollback_check_cron.py
======================
차차기 W6D — roll-back trigger 체크 cron wrapper.

매 schedule 실행:
  *모니터링 대상 step 목록* 각각에 대해 check_rollback.
    trigger=True → emit_rollback_alert (sentinel + 로그 + rollback_events).
    trigger=False → 무동작 (cron 자체는 'ok' 로 cron_runs 에 기록).

본 cron 자체도 cron_runtime 로 추적 — 모니터링의 모니터링.

권장 schedule (Windows Task Scheduler — CRON_GUIDE.md):
  매 시간 정각 (수집·점수 cron 의 정시 후, 빠른 인지).

CLI:
  py rollback_check_cron.py
  py rollback_check_cron.py --threshold 5
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cron_runtime import cron_run
from rollback_monitor import (
    DEFAULT_THRESHOLD, check_rollback, emit_rollback_alert,
)


# 모니터링 대상 cron step 이름 (cron_runs.step 값과 일치).
MONITORED_STEPS = (
    "collect_and_build",
    "precompute_scores_a_prime",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="W6D — rollback 트리거 체크")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                        help=f"연속 실패 임계 (default: {DEFAULT_THRESHOLD}).")
    args = parser.parse_args()

    triggered: list[str] = []
    with cron_run("rollback_check") as ctx:
        for step in MONITORED_STEPS:
            decision = check_rollback(step, threshold=args.threshold)
            if decision.trigger:
                sentinel = emit_rollback_alert(
                    decision,
                    current_default=os.getenv("DEFAULT_MODEL_VERSION"),
                )
                triggered.append(step)
                print(f"[ALERT] {step}: {decision.reason}  sentinel={sentinel.name}")
            else:
                print(f"[ok] {step}: {decision.reason}")
        ctx.report_rows(len(triggered))
    return 0


if __name__ == "__main__":
    sys.exit(main())
