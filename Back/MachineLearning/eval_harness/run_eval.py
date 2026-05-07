"""
eval_harness/run_eval.py
========================
Tier 1.2 (PRD §3.5.1 / 캡스톤 §3.2) — 평가 하네스 진입점.

사용:
    cd Back/MachineLearning
    python -m eval_harness.run_eval --model v9 --out ../../_archive/eval_v9/

산출:
  - report.html  : 슬라이스 × 메트릭 매트릭스 1페이지 (보고서 자산)
  - report.json  : 동일 데이터의 평탄 JSON

설계 원칙:
  - data_loader → slicer 4종 → metric_bundle → report.
  - 데이터·메트릭·리포트 레이어를 분리해 단위 테스트 가능 (slices, metrics).
  - holdout_evaluator 는 *박제* 단발 평가, run_eval 은 *반복 가능한* 슬라이스 분석.
    두 스크립트는 서로의 산출물을 덮지 않는다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# 상위 디렉터리를 sys.path 에 추가해 calibration_metrics·statistics_metrics 임포트 가능.
_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from eval_harness.data_loader import load_eval_dataset, EvalDataset
from eval_harness.metrics     import compute_metric_bundle
from eval_harness.reports     import build_json, render_html
from eval_harness.slices      import (
    slice_by_cap_quartile,
    slice_by_regime,
    slice_by_sector,
    slice_by_time,
)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 슬라이스 → 메트릭 ──────────────────────────────────────────────────────

def _eval_slices(ds: EvalDataset) -> list[dict]:
    """4개 차원의 슬라이스를 모두 만들고 메트릭 산출 → JSON-friendly dict 리스트."""
    out: list[dict] = []

    for slicer, dim_label in [
        (slice_by_time,         "time"),
        (slice_by_sector,       "sector"),
        (slice_by_cap_quartile, "cap_size"),
        (slice_by_regime,       "regime"),
    ]:
        slices = slicer(ds.rows, ds.period_returns)
        log(f"  {dim_label}: {len(slices)} slice(s)")
        for sl in slices:
            # regime 슬라이스는 자체 period 부분집합을 갖는다. 그 외는 전체 periods 사용.
            periods = sl.periods if sl.periods is not None else ds.period_returns
            metrics = compute_metric_bundle(sl.rows, periods)
            out.append({
                "dimension": sl.dimension,
                "key":       sl.key,
                "metrics":   metrics.to_dict(),
            })
    return out


# ── 메인 ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="v9 평가 하네스 — 슬라이스 4 × 메트릭 5")
    parser.add_argument("--model", default="v9", help="model_version (기본 v9)")
    parser.add_argument(
        "--db",
        default=os.getenv(
            "DUCKDB_PATH",
            r"E:\Capstone Data\project_data\db\market_data.duckdb",
        ),
        help="DuckDB 경로",
    )
    parser.add_argument(
        "--out",
        default=str(_HERE.parent.parent.parent.parent / "_archive" / "eval_v9"),
        help="리포트 출력 디렉터리 (기본 _archive/eval_v9/)",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    out_dir = Path(args.out)
    if not db_path.exists():
        log(f"[ERROR] DuckDB 없음: {db_path}")
        return 1

    log("=== eval_harness ===")
    log(f"  DB:    {db_path}")
    log(f"  Model: {args.model}")
    log(f"  Out:   {out_dir}")

    log("Loading dataset …")
    ds = load_eval_dataset(str(db_path), model_version=args.model)
    log(f"  rows={len(ds.rows):,}  periods={len(ds.period_returns)}")
    if ds.rows.empty:
        log("[ERROR] 평가 데이터가 없습니다. (model_version 확인)")
        return 2

    log("Computing overall metrics …")
    overall = compute_metric_bundle(ds.rows, ds.period_returns).to_dict()

    log("Computing slice metrics …")
    slices = _eval_slices(ds)

    out_dir.mkdir(parents=True, exist_ok=True)
    json_payload = build_json(model_version=args.model, overall=overall, slices=slices)
    (out_dir / "report.json").write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"  Wrote {out_dir / 'report.json'}")

    html_text = render_html(model_version=args.model, overall=overall, slices=slices)
    (out_dir / "report.html").write_text(html_text, encoding="utf-8")
    log(f"  Wrote {out_dir / 'report.html'}  ({len(html_text):,} chars)")

    log("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
