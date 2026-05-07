"""
holdout_evaluator.py
====================
Tier 1.1 (PRD §3.5.3 / 캡스톤 §3.1) — v9 모델 holdout 단 1회 평가.

설계 원칙 — *학술적 정직성*:
  - 본 스크립트가 산출하는 모든 결과는 `_archive/holdout_2026_q1_q2/` 에 박제된다.
  - 박제 디렉터리에 이미 결과 파일이 있으면 *기본적으로 실행 거부* (--force 필요).
    이로써 holdout 결과를 보고 v9 정책·하이퍼를 *재선택* 하는 selection bias 를 방지.
  - forward return 측정 가능한 행만 평가 (마지막 ~20거래일 자연 제외).

산출:
  - holdout_v9_report.json  : Sharpe/MDD/alpha/hit-rate/DSR
  - calibration_v9.json     : ECE/Brier/Reliability/Per-slice ECE
  - holdout_v9_summary.md   : 1장짜리 사람이 읽는 요약

사용:
  py -3 holdout_evaluator.py                       # 기본 실행 (이미 박제됐으면 거부)
  py -3 holdout_evaluator.py --dry-run             # 결과 출력만, 파일 저장 안 함
  py -3 holdout_evaluator.py --force               # 박제 덮어쓰기 (errata 추가 시에만)

라벨링:
  prices.close 의 t+20 거래일 수익률 ≥ +5% 이면 양성 (모델 학습 시 라벨 정의와 일치).
  forward 20일이 prices 끝을 넘으면 해당 행 평가 제외.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import duckdb
import numpy as np
import pandas as pd

from calibration_metrics import calibration_bundle, per_slice_ece
from statistics_metrics import compute_sharpe_bundle


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data\project_data"))
DB_PATH = Path(os.getenv("DUCKDB_PATH", str(CAPSTONE_ROOT / "db" / "market_data.duckdb")))
ARCHIVE_DIR = Path(r"E:\Capstone Data\_archive\holdout_2026_q1_q2")

MODEL_VERSION = "v9"
LABEL_THRESHOLD = 0.05      # 모델 학습 시 +5% (meta.json 의 label_threshold)
FORWARD_DAYS = 20           # 거래일 기준


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 데이터 적재 ────────────────────────────────────────────────────────────

def load_holdout_data(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    scores(v9) + prices 를 join 해 (date, ticker, prob_ensemble, fwd_return) 추출.

    forward return = (close[t+20거래일] - close[t]) / close[t]
    20거래일 후 가격이 prices 에 없는 행은 자동 제외.
    """
    log("Loading scores + forward returns from DuckDB ...")
    # scores: 'YYYY-MM-DD' 문자열 / prices: BIGINT YYYYMMDD
    df = con.execute(f"""
        WITH base AS (
            SELECT
                CAST(s.date AS VARCHAR)                          AS date_str,
                CAST(strftime(CAST(s.date AS DATE), '%Y%m%d') AS BIGINT) AS date_int,
                s.ticker,
                s.sector,
                CAST(s.prob_ensemble AS DOUBLE)                  AS prob,
                CAST(s.score AS DOUBLE)                          AS score,
                s.tier
            FROM scores s
            WHERE s.model_version = '{MODEL_VERSION}'
        ),
        joined_today AS (
            SELECT
                b.date_str, b.date_int, b.ticker, b.sector,
                b.prob, b.score, b.tier,
                CAST(p.close AS DOUBLE) AS close_today,
                ROW_NUMBER() OVER (
                    PARTITION BY b.ticker
                    ORDER BY b.date_int
                ) AS row_num
            FROM base b
            JOIN prices p
              ON p.ticker = b.ticker
             AND p.date   = b.date_int
        )
        SELECT *
        FROM joined_today
        ORDER BY ticker, date_int
    """).fetchdf()
    log(f"  Joined scores+prices: {len(df):,} rows")

    # forward 20거래일 close — ticker 별로 shift.
    df = df.sort_values(["ticker", "date_int"]).reset_index(drop=True)
    df["close_fwd"] = df.groupby("ticker")["close_today"].shift(-FORWARD_DAYS)
    df = df.dropna(subset=["close_fwd"]).copy()
    df["fwd_return"] = (df["close_fwd"] - df["close_today"]) / df["close_today"]
    df["label"] = (df["fwd_return"] >= LABEL_THRESHOLD).astype(int)
    df["year"] = df["date_str"].str.slice(0, 4)
    log(f"  After forward-{FORWARD_DAYS}d filter: {len(df):,} rows")
    log(f"  Date range evaluated: {df['date_str'].min()} ~ {df['date_str'].max()}")
    log(f"  Buy-rate (≥+{int(LABEL_THRESHOLD*100)}%): {df['label'].mean():.4f}")
    return df


def load_kospi_returns(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """KOSPI 벤치마크 — 삼성전자(005930) 종가의 forward 20거래일 수익률."""
    df = con.execute(f"""
        SELECT
            date AS date_int,
            CAST(close AS DOUBLE) AS close
        FROM prices
        WHERE ticker = '005930'
        ORDER BY date
    """).fetchdf()
    df = df.sort_values("date_int").reset_index(drop=True)
    df["close_fwd"] = df["close"].shift(-FORWARD_DAYS)
    df = df.dropna(subset=["close_fwd"]).copy()
    df["bench_return"] = (df["close_fwd"] - df["close"]) / df["close"]
    return df[["date_int", "bench_return"]]


# ── 평가 ────────────────────────────────────────────────────────────────────

def evaluate(df: pd.DataFrame, bench: pd.DataFrame) -> dict:
    """
    Holdout 운용 성과 — *non-overlapping* 20거래일 리밸런싱 기준.

    설계 의도:
      - forward 20거래일 수익률을 *매일* 산출하면 holding period 가 겹쳐
        Sharpe·cumulative return 이 비합리적으로 부풀려진다 (overlapping
        backtest bias). 학술 평가에서는 non-overlapping 표본만 사용한다.
      - 따라서 holdout 시작일부터 20거래일 간격으로 리밸런스 시점을 잡고,
        그 시점의 Tier A 평균 forward 20d 수익률만 strategy 시계열로 사용.
      - 결과: 60 거래일 → 3~4개 period (작지만 정직한 표본).
      - 분류 지표(ECE/Brier) 는 별도 함수에서 *전 행* 을 사용 (overlap 무관).
    """
    tier_a = df[df["tier"] == "A"].copy()
    log(f"  Tier A rows: {len(tier_a):,}")

    # 평가 가능한 거래일을 정렬 → FORWARD_DAYS 간격으로 sample.
    eval_dates = sorted(df["date_int"].unique())
    rebalance_dates = eval_dates[::FORWARD_DAYS]
    log(f"  Non-overlapping rebalance dates: {len(rebalance_dates)} "
        f"(every {FORWARD_DAYS} trading days)")

    rows = []
    for rd in rebalance_dates:
        picks = tier_a[tier_a["date_int"] == rd]
        if picks.empty:
            continue
        strat_ret = float(picks["fwd_return"].mean())
        bench_row = bench[bench["date_int"] == rd]
        bench_ret = float(bench_row["bench_return"].iloc[0]) if not bench_row.empty else float("nan")
        rows.append({
            "date_int":     int(rd),
            "n_picks":      int(len(picks)),
            "strat_return": strat_ret,
            "bench_return": bench_ret,
        })
    period_df = pd.DataFrame(rows).dropna(subset=["bench_return"])
    log(f"  Period series (non-overlapping): {len(period_df)} returns")

    # 각 period 가 ~20거래일이므로 연환산 = 252/20 ≈ 12.6.
    periods_per_year = max(1, int(round(252 / FORWARD_DAYS)))

    if period_df.empty:
        empty_bundle = compute_sharpe_bundle(np.array([]), periods_per_year)
        return {
            "evaluated_period": {"start": None, "end": None, "n_periods": 0},
            "model_version": MODEL_VERSION,
            "label_threshold": LABEL_THRESHOLD,
            "forward_days": FORWARD_DAYS,
            "rebalance_kind": f"non-overlapping every {FORWARD_DAYS} trading days",
            "strategy":  empty_bundle.to_dict(),
            "benchmark_kospi_proxy_005930": empty_bundle.to_dict(),
            "alpha_vs_kospi": empty_bundle.to_dict(),
        }

    period_df["alpha"] = period_df["strat_return"] - period_df["bench_return"]

    sharpe_bundle = compute_sharpe_bundle(period_df["strat_return"].values, periods_per_year)
    bench_bundle  = compute_sharpe_bundle(period_df["bench_return"].values, periods_per_year)
    alpha_bundle  = compute_sharpe_bundle(period_df["alpha"].values,        periods_per_year)

    cum_strat = float((1 + period_df["strat_return"]).prod() - 1)
    cum_bench = float((1 + period_df["bench_return"]).prod() - 1)
    cum_alpha = cum_strat - cum_bench

    # MDD on the period equity curve.
    cum_path = (1 + period_df["strat_return"]).cumprod().values
    peak = np.maximum.accumulate(cum_path)
    drawdown = (cum_path / peak - 1.0)
    mdd = float(drawdown.min()) if len(drawdown) else 0.0

    hit_rate = float((period_df["strat_return"] > 0).mean())
    avg_picks = float(period_df["n_picks"].mean())

    return {
        "evaluated_period": {
            "start_int": int(period_df["date_int"].min()),
            "end_int":   int(period_df["date_int"].max()),
            "n_periods": int(len(period_df)),
            "n_evaluable_days_total": int(len(eval_dates)),
        },
        "model_version": MODEL_VERSION,
        "label_threshold": LABEL_THRESHOLD,
        "forward_days": FORWARD_DAYS,
        "rebalance_kind": f"non-overlapping every {FORWARD_DAYS} trading days",
        "periods_per_year_assumed": periods_per_year,
        "tier_a_picks_per_period_avg": round(avg_picks, 2),
        "strategy": {
            **sharpe_bundle.to_dict(),
            "cumulative_return": round(cum_strat, 4),
            "max_drawdown":      round(mdd, 4),
            "hit_rate_periodwise": round(hit_rate, 4),
        },
        "benchmark_kospi_proxy_005930": {
            **bench_bundle.to_dict(),
            "cumulative_return": round(cum_bench, 4),
        },
        "alpha_vs_kospi": {
            **alpha_bundle.to_dict(),
            "cumulative_alpha": round(cum_alpha, 4),
        },
    }


def evaluate_calibration(df: pd.DataFrame) -> dict:
    """ECE·Brier·Reliability + 슬라이스(연도·섹터)별 ECE."""
    y_true = df["label"].values
    y_prob = df["prob"].values
    bundle = calibration_bundle(y_true, y_prob, n_bins=10)
    by_year   = per_slice_ece(y_true, y_prob, df["year"].values,   n_bins=10, min_count=200)
    by_sector = per_slice_ece(
        y_true, y_prob, df["sector"].fillna("Unknown").values,
        n_bins=10, min_count=200,
    )
    return {
        "overall": bundle.to_dict(),
        "by_year":   by_year,
        "by_sector": by_sector,
    }


# ── 박제 ────────────────────────────────────────────────────────────────────

def write_archive(report: dict, calib: dict, *, dry_run: bool, force: bool) -> int:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ARCHIVE_DIR / "holdout_v9_report.json"
    calib_path  = ARCHIVE_DIR / "calibration_v9.json"
    summary_path = ARCHIVE_DIR / "holdout_v9_summary.md"

    if not dry_run and not force:
        if report_path.exists() or calib_path.exists():
            log(f"[REFUSED] 이미 박제된 파일이 존재합니다 → {ARCHIVE_DIR}")
            log("  selection bias 방지. 재평가는 새 디렉터리에서. (--force 명시 시 덮어씀)")
            return 2

    if dry_run:
        log("--- dry-run preview ---")
        print(json.dumps({"report": report, "calibration": calib},
                         ensure_ascii=False, indent=2))
        return 0

    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    payload = {
        "sealed_at": timestamp,
        "warning":   "박제됨. 본 결과를 보고 v9 정책·하이퍼파라미터를 재선택하면 selection bias 발생.",
        **report,
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  Wrote {report_path.name}")

    calib_payload = {
        "sealed_at":      timestamp,
        "model_version":  MODEL_VERSION,
        "n_bins":         10,
        **calib,
    }
    calib_path.write_text(json.dumps(calib_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  Wrote {calib_path.name}")

    # 사람이 읽는 요약.
    s = report["strategy"]
    a = report["alpha_vs_kospi"]
    o = calib["overall"]
    md = (
        f"# v9 Holdout 박제 요약 (2026 Q1·Q2)\n\n"
        f"- **봉인 시각**: {timestamp}\n"
        f"- **리밸런싱**: {report['rebalance_kind']}\n"
        f"- **평가 period 수**: {report['evaluated_period']['n_periods']} "
        f"(전체 거래일 {report['evaluated_period']['n_evaluable_days_total']}일)\n"
        f"- **Tier A period당 평균 종목 수**: {report['tier_a_picks_per_period_avg']}\n\n"
        f"## 운용 성과 (non-overlapping)\n\n"
        f"| 지표 | 값 |\n"
        f"|------|----|\n"
        f"| Sharpe (annualized, p/y={report['periods_per_year_assumed']}) | {s['sharpe_ratio']} |\n"
        f"| Cumulative Return   | {s['cumulative_return']*100:.2f}% |\n"
        f"| Max Drawdown        | {s['max_drawdown']*100:.2f}% |\n"
        f"| Period-wise hit-rate | {s['hit_rate_periodwise']*100:.1f}% |\n"
        f"| Cumulative Alpha vs KOSPI | {a['cumulative_alpha']*100:.2f}% |\n"
        f"| **PSR (threshold=0)** | **{s['psr_threshold_0']}** |\n"
        f"| **DSR (n_trials=1)**  | **{s['dsr_n1']}** |\n\n"
        f"## 캘리브레이션\n\n"
        f"- ECE (10-bin): **{o['ece']}**\n"
        f"- Brier score: {o['brier']}\n"
        f"- 평가 표본 수: {o['n_observations']:,}\n"
        f"- 슬라이스별 ECE: 연도 {len(calib['by_year'])} 개 / 섹터 {len(calib['by_sector'])} 개\n\n"
        f"## 정직성 선언\n\n"
        f"본 결과는 `_archive/holdout_2026_q1_q2/` 에 영구 박제됩니다. 본 페이지를 보고 "
        f"v9 의 정책·하이퍼파라미터를 *수정하면* selection bias 가 발생하므로 절대 금지. "
        f"새 모델 비교는 동일 분할로 별도 디렉터리에 박제합니다.\n"
    )
    summary_path.write_text(md, encoding="utf-8")
    log(f"  Wrote {summary_path.name}")

    return 0


# ── 메인 ───────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="v9 holdout 평가 (단 1회 박제)")
    parser.add_argument("--dry-run", action="store_true", help="저장 없이 결과만 출력")
    parser.add_argument("--force",   action="store_true",
                        help="박제 덮어쓰기 (errata 추가 시에만 명시적으로)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        log(f"[ERROR] DuckDB 없음: {DB_PATH}")
        return 1
    log("=== v9 Holdout Evaluator ===")
    log(f"  DB:      {DB_PATH}")
    log(f"  Archive: {ARCHIVE_DIR}")
    log(f"  Forward: {FORWARD_DAYS} trading days, label ≥ +{int(LABEL_THRESHOLD*100)}%")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        df = load_holdout_data(con)
        if df.empty:
            log("[ERROR] holdout 평가용 데이터가 없습니다.")
            return 3
        bench = load_kospi_returns(con)
        report = evaluate(df, bench)
        calib  = evaluate_calibration(df)
    finally:
        con.close()

    return write_archive(report, calib, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
