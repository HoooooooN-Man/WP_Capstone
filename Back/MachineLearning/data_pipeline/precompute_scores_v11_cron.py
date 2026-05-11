"""
precompute_scores_v11_cron.py
=============================
차차기 W6C — v11 점수 적재 cron wrapper.

트리거 정책 (사용자 권고 — 혼합 (다)):
  매일 cron 실행 → prices 새 데이터 들어왔으면 적재, 아니면 'no_change' 기록.
    데이터 변화 판정:
      MAX(prices.date)  > MAX(scores.date WHERE model_version = ?)
    → 적재 필요 (precompute_scores_v11.main 호출)
    → 같거나 작으면 변화 없음 — no_change 기록 후 종료 (sentinel 미생성).

  *cron 살아있는 신호 + 불필요한 적재 회피.* manual batch 4/29 정지 같은 상황에서
  같은 점수 매일 다시 적재하는 낭비 회피.

사용 (Windows Task Scheduler — CRON_GUIDE.md §2 참조):
  매일 19:30 KST (수집 cron 18:00 완료 후 충분 시간).

CLI:
  py precompute_scores_v11_cron.py                       # default variant=a_prime
  py precompute_scores_v11_cron.py --variant a_prime_dart
  py precompute_scores_v11_cron.py --force               # 변화 감지 무시, 무조건 재적재
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cron_runtime import cron_run

ML_DIR = Path(__file__).resolve().parents[1]
PRECOMPUTE_SCRIPT = ML_DIR / "precompute_scores_v11.py"
DEFAULT_DUCKDB = Path(os.getenv(
    "DUCKDB_PATH",
    r"E:\Capstone Data\project_data\db\market_data.duckdb",
))


def detect_change(duckdb_path: Path, model_version: str) -> tuple[bool, Optional[int], Optional[int]]:
    """
    prices.MAX(date) vs scores.MAX(date WHERE model_version=?) 비교.
    return: (needs_update, prices_max, scores_max).
    """
    if not duckdb_path.exists():
        # DB 부재 — 적재 필요 (또는 caller 가 판단). 보수적으로 True.
        return True, None, None
    import duckdb
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        prices_max = con.execute("SELECT MAX(date) FROM prices").fetchone()[0]
        try:
            scores_max = con.execute(
                "SELECT MAX(date) FROM scores WHERE model_version = ?",
                [model_version],
            ).fetchone()[0]
        except Exception:
            scores_max = None    # scores 테이블 부재 — 적재 필요
    finally:
        con.close()
    # DuckDB BIGINT(YYYYMMDD) or DATE — int 비교로 통일.
    def _to_int(v) -> Optional[int]:
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return int(str(v).replace("-", ""))
    pm = _to_int(prices_max)
    sm = _to_int(scores_max)
    needs = (sm is None) or (pm is not None and pm > sm)
    return needs, pm, sm


def run_precompute(variant: str) -> int:
    """precompute_scores_v11.py subprocess 호출. returncode 반환."""
    cmd = [sys.executable, str(PRECOMPUTE_SCRIPT),
           "--variant", variant, "--overwrite"]
    result = subprocess.run(cmd, cwd=str(ML_DIR.parents[1]),
                            check=False, env=os.environ.copy())
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="W6C — v11 점수 적재 cron")
    parser.add_argument("--variant", default="a_prime",
                        help="모델 variant (default: a_prime — W7B 운영).")
    parser.add_argument("--force",   action="store_true",
                        help="변화 감지 무시, 무조건 재적재.")
    args = parser.parse_args()

    model_version = f"v11{args.variant}"

    if not PRECOMPUTE_SCRIPT.exists():
        print(f"[ERROR] precompute_scores_v11.py 없음: {PRECOMPUTE_SCRIPT}",
              file=sys.stderr)
        return 2

    with cron_run(f"precompute_scores_{args.variant}") as ctx:
        needs, prices_max, scores_max = detect_change(DEFAULT_DUCKDB, model_version)
        if not args.force and not needs:
            ctx.mark_no_change(
                f"prices.MAX(date)={prices_max} <= scores.MAX(date)={scores_max}"
            )
            print(f"[no_change] prices={prices_max} scores={scores_max} -- skip")
            return 0
        print(f"[update] prices={prices_max} scores={scores_max} (force={args.force})")
        rc = run_precompute(args.variant)
        if rc != 0:
            raise RuntimeError(
                f"precompute_scores_v11 exited {rc}. "
                f"check logs/cron_status.log + logs/FAIL_*.flag"
            )
        # rows_affected 는 precompute_scores_v11 stdout 미파싱 — 차차차기 정밀화.
    return 0


if __name__ == "__main__":
    sys.exit(main())
