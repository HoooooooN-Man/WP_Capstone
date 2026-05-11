"""
collect_cron.py
===============
차차기 W6B — collect_and_build.py 를 cron_run context 로 감싼 wrapper.

목적:
  Task Scheduler·cron 이 본 스크립트를 호출 → 자동 추적·실패 알림.
  collect_and_build.py 자체는 *manual 실행 호환* 그대로 유지.

흐름:
  cron_run("collect_and_build") 안에서 collect_and_build.main() 호출.
  성공: cron_runs.status='ok', rows_affected = 신규 OHLCV 행 수.
  실패: status='failed', sentinel 생성, 예외 stdout 으로 전파 (Task Scheduler 도 fail 인지).

사용 (Windows Task Scheduler):
  Program/script:  E:\Capstone Data\WP_Capstone-main\.venv\Scripts\python.exe
  Arguments:       Back\MachineLearning\data_pipeline\collect_cron.py
  Start in:        E:\Capstone Data\WP_Capstone-main
  환경변수:        KRX_ID, KRX_PW (작업 등록 시 명시 또는 시스템 env)

사용 (cron / Linux):
  # daily at 18:00 KST
  0 18 * * * cd /path/to/WP_Capstone && \\
      python Back/MachineLearning/data_pipeline/collect_cron.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cron_runtime import cron_run


COLLECT_SCRIPT = Path(__file__).resolve().parent / "collect_and_build.py"


def main() -> int:
    if not COLLECT_SCRIPT.exists():
        print(f"[ERROR] collect_and_build.py 없음: {COLLECT_SCRIPT}", file=sys.stderr)
        return 2

    with cron_run("collect_and_build") as ctx:
        # subprocess 로 호출 — collect_and_build 가 sys.exit 호출하거나 예외 던져도
        # 본 wrapper 가 격리. returncode != 0 → 예외 raise → cron_run 이 실패 기록.
        cmd = [sys.executable, str(COLLECT_SCRIPT)]
        # CLI 인자 그대로 전달 (--start·--end·--no-collect 등).
        cmd.extend(sys.argv[1:])
        result = subprocess.run(cmd, cwd=str(COLLECT_SCRIPT.parents[3]),
                                check=False, env=os.environ.copy())
        if result.returncode != 0:
            raise RuntimeError(
                f"collect_and_build exited {result.returncode}. "
                f"check logs/cron_status.log + logs/FAIL_*.flag"
            )
        # rows_affected 는 collect_and_build stdout 파싱이 필요한데 본 wrapper 는
        # subprocess 라 stdout 캡처 안 함. 차차차기 — 직접 import 방식 전환 시 정밀화.
    return 0


if __name__ == "__main__":
    sys.exit(main())
