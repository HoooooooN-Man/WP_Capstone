"""
playground_grid.py
==================
Tier 2.5 (차별화 §2.4 / 캡스톤 §5.5) — 사용자 정책 슬라이더용 사전계산 grid.

캡스톤 축약:
  - 슬라이더 9개 정책 파라미터 중 *2개만* 변동: `tier_a_cutoff`, `top_k`.
  - 18 조합 × non-overlapping 20거래일 리밸런싱 = 빠른 사전계산.
  - 각 조합의 Sharpe/cumulative return/MDD 를 grid JSON 으로 박제.
  - 프론트는 lookup 만 — 실시간 백테스트 X (캡스톤 §5.5 명시).

산출: `_archive/playground/grid_v9.json`

사용:
  python playground_grid.py                # full run
  python playground_grid.py --dry-run      # 결과 출력만
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from statistics_metrics import compute_sharpe_bundle


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data\project_data"))
DB_PATH = Path(os.getenv("DUCKDB_PATH", str(CAPSTONE_ROOT / "db" / "market_data.duckdb")))
OUT_DIR = Path(r"E:\Capstone Data\_archive\playground")

MODEL_VERSION = "v9"
FORWARD_DAYS = 20
PERIODS_PER_YEAR = 13

CUTOFFS = [85, 88, 90, 93, 95, 97]
TOP_KS  = [10, 20, 50]


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_eval_data(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """holdout 행 + forward return 부착."""
    df = con.execute("""
        SELECT
            CAST(s.date AS VARCHAR)                          AS date_str,
            CAST(strftime(CAST(s.date AS DATE), '%Y%m%d') AS BIGINT) AS date_int,
            s.ticker,
            CAST(s.score AS DOUBLE)                          AS score,
            CAST(p.close AS DOUBLE)                          AS close_today
        FROM scores s
        JOIN prices p
          ON p.ticker = s.ticker
         AND p.date   = CAST(strftime(CAST(s.date AS DATE), '%Y%m%d') AS BIGINT)
        WHERE s.model_version = ?
        ORDER BY s.ticker, s.date
    """, [MODEL_VERSION]).fetchdf()
    df = df.sort_values(["ticker", "date_int"]).reset_index(drop=True)
    df["close_fwd"] = df.groupby("ticker")["close_today"].shift(-FORWARD_DAYS)
    df = df.dropna(subset=["close_fwd"]).copy()
    df["fwd_return"] = (df["close_fwd"] - df["close_today"]) / df["close_today"]
    return df


def load_bench(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute("""
        SELECT date AS date_int, CAST(close AS DOUBLE) AS close
        FROM prices
        WHERE ticker = '005930'
        ORDER BY date
    """).fetchdf()
    df = df.sort_values("date_int").reset_index(drop=True)
    df["close_fwd"] = df["close"].shift(-FORWARD_DAYS)
    df = df.dropna(subset=["close_fwd"]).copy()
    df["bench_return"] = (df["close_fwd"] - df["close"]) / df["close"]
    return df[["date_int", "bench_return"]]


def evaluate_combo(
    df: pd.DataFrame, bench: pd.DataFrame,
    cutoff: int, top_k: int,
) -> dict:
    """단일 (cutoff, top_k) 조합의 성과."""
    eval_dates = sorted(df["date_int"].unique())
    rebalance_dates = eval_dates[::FORWARD_DAYS]

    rows = []
    for rd in rebalance_dates:
        day = df[df["date_int"] == rd]
        # cutoff 이상의 종목만 → 점수 내림차순 → top_k.
        eligible = day[day["score"] >= cutoff].sort_values("score", ascending=False).head(top_k)
        if eligible.empty:
            continue
        b = bench[bench["date_int"] == rd]
        if b.empty:
            continue
        rows.append({
            "date_int":     int(rd),
            "n_picks":      int(len(eligible)),
            "strat_return": float(eligible["fwd_return"].mean()),
            "bench_return": float(b["bench_return"].iloc[0]),
        })
    period_df = pd.DataFrame(rows)
    if period_df.empty:
        return {
            "cutoff": cutoff, "top_k": top_k,
            "n_periods": 0,
            "sharpe": None, "cumulative_return": None,
            "max_drawdown": None, "alpha_cum": None,
            "avg_picks": 0,
            "note": "조건에 맞는 종목 없음",
        }

    sb = compute_sharpe_bundle(period_df["strat_return"].values, periods_per_year=PERIODS_PER_YEAR)
    cum_strat = float((1 + period_df["strat_return"]).prod() - 1)
    cum_bench = float((1 + period_df["bench_return"]).prod() - 1)
    cum_path = (1 + period_df["strat_return"]).cumprod().values
    peak = np.maximum.accumulate(cum_path)
    drawdown = (cum_path / peak - 1.0)
    mdd = float(drawdown.min()) if len(drawdown) else 0.0

    return {
        "cutoff":             cutoff,
        "top_k":              top_k,
        "n_periods":          int(len(period_df)),
        "avg_picks":          float(round(period_df["n_picks"].mean(), 1)),
        "sharpe":             round(sb.sharpe_ratio, 4),
        "cumulative_return":  round(cum_strat, 4),
        "benchmark_return":   round(cum_bench, 4),
        "alpha_cum":          round(cum_strat - cum_bench, 4),
        "max_drawdown":       round(mdd, 4),
        "psr_threshold_0":    round(sb.psr_threshold_0, 4),
        "note": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force",   action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        log(f"[ERROR] DuckDB 없음: {DB_PATH}")
        return 1

    log("=== Playground Grid (Tier 2.5) ===")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        df = load_eval_data(con)
        bench = load_bench(con)
    finally:
        con.close()
    log(f"  Eval rows: {len(df):,}  bench rows: {len(bench):,}")

    log(f"  Combinations: {len(CUTOFFS)} cutoffs × {len(TOP_KS)} top_k = {len(CUTOFFS)*len(TOP_KS)}")

    combos = []
    for c in CUTOFFS:
        for k in TOP_KS:
            combos.append(evaluate_combo(df, bench, c, k))
    log(f"  Computed {len(combos)} combinations")

    grid = {
        "schema_version": "1.0",
        "generated_at":   datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_version":  MODEL_VERSION,
        "axis_cutoff":    CUTOFFS,
        "axis_top_k":     TOP_KS,
        "rebalance_kind": f"non-overlapping every {FORWARD_DAYS} trading days",
        "periods_per_year_assumed": PERIODS_PER_YEAR,
        "note": (
            "캡스톤 시연용 사전계산 grid. n_periods=3 (holdout 4개월) 으로 표본이 작아 "
            "통계적 유의성은 약함. 사용자가 슬라이더로 조작해 *모델을 만질 수 있다* 는 "
            "경험을 제공하는 것이 1차 목적."
        ),
        "combinations": combos,
    }

    if args.dry_run:
        print(json.dumps(grid, ensure_ascii=False, indent=2))
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "grid_v9.json"
    if out_path.exists() and not args.force:
        log(f"[REFUSED] 이미 박제됨: {out_path}")
        log("  --force 명시 시에만 덮어쓰기.")
        return 2
    out_path.write_text(json.dumps(grid, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
