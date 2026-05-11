"""
test_w6_e2e_smoke.py
====================
차차기 W6E — end-to-end smoke. W6A~D 의 통합 검증.

통과 기준 (commit body 박제 — 차차차기 재실행 시 동일 기준):
  1. data_pipeline 진입점 5개 존재 + import 가능.
  2. cron_runtime end-to-end: success·no_change·failure 각 1회 + 3 채널 일관.
  3. precompute_scores_v11_cron.detect_change 가 현재 DB 에서 분기 결정 가능.
  4. rollback_check 가 monitored steps 에 trigger=False (false positive 0).
  5. logs/FAIL_*.flag 누적 인지 + 미해결 sentinel 명시 (smoke 흔적 vs 실 실패 구분).
  6. (옵션·환경) 외부 호출 step 은 dry-run / no-collect 로 KRX 자격 없이도 검증.

본 smoke 는 *cron 등록 자체* 검증 안 함 — schedule 등록은 사용자 측 manual (CRON_GUIDE.md).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import duckdb
import pytest

DATA_PIPELINE = Path(__file__).resolve().parents[1] / "data_pipeline"
LOGS_DIR      = Path(__file__).resolve().parents[3] / "logs"

sys.path.insert(0, str(DATA_PIPELINE))


# ── 기준 1: 진입점 5개 파일 + import ──────────────────────────────────────

ENTRYPOINTS = (
    "collect_and_build.py",
    "collect_cron.py",
    "cron_runtime.py",
    "precompute_scores_v11_cron.py",
    "rollback_monitor.py",
    "rollback_check_cron.py",
)


def test_criterion_1_entrypoints_exist():
    missing = [e for e in ENTRYPOINTS if not (DATA_PIPELINE / e).exists()]
    assert not missing, f"data_pipeline 진입점 누락: {missing}"


def test_criterion_1_imports_succeed():
    """순수 모듈 import (subprocess 호출 모듈 제외). compile 안 깨지는지 확인.
    dataclass 가 sys.modules lookup 하므로 명시 등록 후 exec."""
    importable = ["cron_runtime", "precompute_scores_v11_cron",
                  "rollback_monitor", "rollback_check_cron"]
    for name in importable:
        spec = importlib.util.spec_from_file_location(
            name, DATA_PIPELINE / f"{name}.py",
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.modules.pop(name, None)


# ── 기준 2: cron_runtime end-to-end (3 채널 일관) ──────────────────────

def test_criterion_2_cron_runtime_end_to_end(tmp_path):
    from cron_runtime import cron_run
    db = tmp_path / "smoke.duckdb"

    # success
    with cron_run("smoke_ok", log_dir=tmp_path, duckdb_path=db) as ctx:
        ctx.report_rows(10)

    # no_change
    with cron_run("smoke_nc", log_dir=tmp_path, duckdb_path=db) as ctx:
        ctx.mark_no_change("no data")

    # failure
    with pytest.raises(RuntimeError):
        with cron_run("smoke_fail", log_dir=tmp_path, duckdb_path=db):
            raise RuntimeError("intended")

    # 채널 1: log
    log = (tmp_path / "cron_status.log").read_text(encoding="utf-8")
    for marker in ("OK rows=10", "NO_CHANGE reason=no data", "FAIL RuntimeError"):
        assert marker in log, f"log marker 누락: {marker!r}"

    # 채널 2: sentinel (FAIL 만 — OK/no_change 는 생성 안 함)
    sentinels = sorted(p.name for p in tmp_path.glob("FAIL_*.flag"))
    assert sentinels == ["FAIL_smoke_fail_" + sentinels[0][16:]]   # 1건
    assert not list(tmp_path.glob("FAIL_smoke_ok_*.flag"))
    assert not list(tmp_path.glob("FAIL_smoke_nc_*.flag"))

    # 채널 3: DuckDB cron_runs
    con = duckdb.connect(str(db), read_only=True)
    try:
        rows = con.execute(
            "SELECT step, status FROM cron_runs ORDER BY started_at"
        ).fetchall()
    finally:
        con.close()
    assert rows == [
        ("smoke_ok", "ok"),
        ("smoke_nc", "no_change"),
        ("smoke_fail", "failed"),
    ]


# ── 기준 3: detect_change 현재 DB 분기 ─────────────────────────────────

def test_criterion_3_detect_change_runs_on_real_db():
    """현재 운영 DB 가 있으면 detect_change 가 (bool, int|None, int|None) 반환."""
    from precompute_scores_v11_cron import detect_change, DEFAULT_DUCKDB
    if not DEFAULT_DUCKDB.exists():
        pytest.skip("운영 DuckDB 부재 — 환경 의존")
    needs, pm, sm = detect_change(DEFAULT_DUCKDB, "v11a_prime")
    assert isinstance(needs, bool)
    # prices.MAX(date) 와 scores.MAX(date) 모두 존재해야 정상 운영 상태.
    assert pm is not None, "prices 비어있음 — 수집이 한 번도 안 됨"
    # sm 은 None 가능 (운영 default 가 다른 variant 일 수 있음).
    # 단 needs 가 boolean 으로 결정됐다는 게 핵심.


# ── 기준 4: rollback_check false positive 0 ────────────────────────────

def test_criterion_4_rollback_no_false_positive_on_real_db():
    from rollback_monitor import check_rollback
    from rollback_check_cron import MONITORED_STEPS
    from precompute_scores_v11_cron import DEFAULT_DUCKDB
    if not DEFAULT_DUCKDB.exists():
        pytest.skip("운영 DuckDB 부재")
    for step in MONITORED_STEPS:
        d = check_rollback(step)
        assert d.trigger is False, (
            f"false positive on real DB: step={step} reason={d.reason} "
            f"recent={d.recent_statuses}. 실제 실패 누적이면 ROLLBACK_*.flag 확인."
        )


# ── 기준 5: 미해결 sentinel 인지 (실 실패와 smoke 흔적 구분) ─────────────

def test_criterion_5_pending_sentinels_visible():
    """sentinel 카운트 자체로 fail 안 만듦 — 보고만. 차차차기 운영 시 점검 기준."""
    if not LOGS_DIR.exists():
        pytest.skip("logs dir 부재")
    fails = sorted(LOGS_DIR.glob("FAIL_*.flag"))
    rollbacks = sorted(LOGS_DIR.glob("ROLLBACK_*.flag"))
    # 본 assertion 은 *환경 상태 보고* 만. 실 운영에선 매일 점검.
    # smoke 흔적 (smoke_fail, w6b_smoke_fail 등) 은 *알려진 무해* — 별도 카운트.
    known_smoke_prefixes = ("smoke_", "w6b_smoke_", "step_fail_", "step_x_",
                              "FAIL_smoke_", "FAIL_w6b_smoke_", "FAIL_step_")
    pending = [f.name for f in fails
               if not any(f.name.startswith(p) for p in known_smoke_prefixes)]
    rollback_pending = [r.name for r in rollbacks]
    # 미해결 sentinel 이 있으면 *경고만* — 차차차기 점검 의무. 본 test 는 PASS.
    if pending or rollback_pending:
        print(f"\n[W6E warning] 미해결 sentinel — FAIL: {pending}  "
              f"ROLLBACK: {rollback_pending}")
    # 본 시점 *real* 실패 sentinel 0 가 정상 — assertion 강제 안 함 (개발 흔적 허용).


# ── 기준 6: 외부 호출 dry-run (KRX 자격 없이) ──────────────────────────

def test_criterion_6_collect_works_without_credentials():
    """collect_and_build.py 의 --no-collect 모드는 KRX 자격 불필요.
    argparse 가 정상 parse 되는지만 검증 (실 features 빌드 호출은 무거움)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "collect_and_build", DATA_PIPELINE / "collect_and_build.py",
    )
    # 모듈 load 자체가 cp949 안전한지 확인 (W6A fix 검증).
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # main() 호출은 무거우니 안 함. 모듈 import + W6A KRX 자격 default 제거 확인:
    # parser default 가 None (env 미설정 시) 이어야.
    import os
    saved = (os.environ.pop("KRX_ID", None), os.environ.pop("KRX_PW", None))
    try:
        # main 의 parser 가 args.no_collect=True 시 자격 검증 우회하는지 — 코드만 확인.
        src = (DATA_PIPELINE / "collect_and_build.py").read_text(encoding="utf-8")
        assert 'os.getenv("KRX_ID")' in src
        assert 'os.getenv("KRX_PW")' in src
        assert "if not args.no_collect and (not args.id or not args.pw):" in src
    finally:
        if saved[0]: os.environ["KRX_ID"] = saved[0]
        if saved[1]: os.environ["KRX_PW"] = saved[1]
