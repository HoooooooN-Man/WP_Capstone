"""
infer_v11_holdout.py
====================
W7A Step 2 — v11{variant} 모델로 holdout (2026 Q1·Q2) 추론 + portfolio backtest.

목적:
  v9 (`_archive/holdout_2026_q1_q2/holdout_v9_report.json`) 와 *동일 분할·동일 metric*
  으로 v11 비교. 봉인 정책 준수 — 새 디렉터리에 추가 박제만, v9 결과 덮어쓰지 않음.

흐름:
  1. v11{variant} model.txt + feature_cols.json 로드.
  2. data_pipeline/inference_input_v5.parquet 로드 → sanitize_feature_names → 67 features 추출.
  3. LightGBM predict → score → group=date 백분위·rank.
  4. Portfolio backtest:
       - 매 20거래일 non-overlapping 리밸런싱 (v9 와 동일).
       - Tier A: top 151 종목 (v9 평균 종목 수 = 151.0; 봉인 README §운용 성과).
       - period_return = mean(fwd_return_20d ∀ top 151) — multi_labels 사용.
       - KOSPI 동일 period 누적 수익률 → alpha.
       - Sharpe annualized (periods/year=13, v9 와 동일).
  5. 박제: `_archive/eval_v11/holdout_2026_q1_q2_<variant>.json`.

사용:
  py infer_v11_holdout.py --variant a_prime
  py infer_v11_holdout.py --variant a_prime --top-k 100   # 다른 K
  py infer_v11_holdout.py --variant a_prime --dry-run     # 박제 생략
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_lambdarank_v11 import sanitize_feature_names  # 학습 때와 동일 sanitize


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data"))
INFER_PARQUET = CAPSTONE_ROOT / "data_pipeline" / "inference_input_v5.parquet"
KOSPI_PARQUET = CAPSTONE_ROOT / "data_pipeline" / "raw_index_fx.parquet"  # 2026 KOSPI
DUCKDB_PATH   = CAPSTONE_ROOT / "project_data" / "db" / "market_data.duckdb"
MODELS_ROOT   = CAPSTONE_ROOT / "project_data" / "models"
ARCHIVE_ROOT  = CAPSTONE_ROOT / "_archive" / "eval_v11"

HOLDOUT_START = "2026-01-02"
HOLDOUT_END   = "2026-04-29"
REBALANCE_DAYS = 20            # v9 holdout: non-overlapping 매 20거래일
PERIODS_PER_YEAR = 13          # v9 와 동일 (≈252/20)
DEFAULT_TOP_K  = 151           # v9 Tier A 평균 종목 수


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 1) 추론 ─────────────────────────────────────────────────────────────────

def load_model(variant: str) -> tuple[lgb.Booster, list[str], dict]:
    model_dir = MODELS_ROOT / f"v11{variant}"
    if not model_dir.exists():
        raise FileNotFoundError(f"모델 없음: {model_dir}")
    booster = lgb.Booster(model_file=str(model_dir / "model.txt"))
    feature_cols = json.loads((model_dir / "feature_cols.json").read_text(encoding="utf-8"))
    meta = json.loads((model_dir / "meta.json").read_text(encoding="utf-8"))
    return booster, feature_cols, meta


def predict_holdout(booster, feature_cols: list[str]) -> pd.DataFrame:
    df = pd.read_parquet(INFER_PARQUET)
    df = sanitize_feature_names(df)
    df["date"] = pd.to_datetime(df["date"])
    log(f"  inference rows: {len(df):,}  date {df['date'].min().date()}~{df['date'].max().date()}")

    # 차차기 W5E — feature_cols 에 dart_* 가 있으면 DuckDB disclosures 에서 build·join.
    dart_needed = [c for c in feature_cols if c.startswith("dart_")]
    if dart_needed:
        log(f"  attaching DART features ({len(dart_needed)}) for holdout …")
        from dart_features import build_features_table, load_disclosures_from_duckdb
        disc = load_disclosures_from_duckdb(str(DUCKDB_PATH))
        target_dt = df[["ticker", "date"]].copy()
        feats = build_features_table(disc, target_dt)
        df = df.merge(feats, on=["ticker", "date"], how="left")
        df[dart_needed] = df[dart_needed].fillna(0).astype("int32")

    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"holdout features 에 {len(missing)} columns 누락: {missing[:5]}...")

    X = df[feature_cols].astype(np.float32).fillna(0.0).to_numpy()
    df["score"] = booster.predict(X, num_iteration=booster.best_iteration)
    df["rank_in_date"] = df.groupby("date")["score"].rank(method="first", ascending=False).astype(int)
    return df[["date", "ticker", "score", "rank_in_date"]]


# ── 2) Portfolio backtest ──────────────────────────────────────────────────

def load_fwd_returns(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """multi_labels.fwd_return_20d (W4) — holdout 기간만."""
    start_int = int(HOLDOUT_START.replace("-", ""))
    end_int   = int(HOLDOUT_END.replace("-", ""))
    df = con.execute(f"""
        SELECT date, ticker, fwd_return_20d
        FROM multi_labels
        WHERE date BETWEEN {start_int} AND {end_int}
          AND fwd_return_20d IS NOT NULL
    """).fetchdf()
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d")
    return df


def load_kospi_close() -> pd.DataFrame:
    """raw_index_fx.parquet 에서 holdout 기간 KOSPI close.
    market_indices DuckDB 는 2025-12-31 까지만 — 2026 은 raw parquet 만 보유.
    """
    df = pd.read_parquet(KOSPI_PARQUET)
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"] >= HOLDOUT_START) & (df["date"] <= HOLDOUT_END)]
    df = df.dropna(subset=["kospi_close"]).sort_values("date").reset_index(drop=True)
    return df[["date", "kospi_close"]]


def rebalance_dates(trading_dates: list[pd.Timestamp], rebalance: int) -> list[pd.Timestamp]:
    """non-overlapping rebalancing 시작일."""
    return [trading_dates[i] for i in range(0, len(trading_dates) - rebalance + 1, rebalance)]


def kospi_period_return(kospi: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> float:
    sub = kospi[(kospi["date"] >= start) & (kospi["date"] <= end)]
    if len(sub) < 2:
        return float("nan")
    return float(sub["kospi_close"].iloc[-1] / sub["kospi_close"].iloc[0] - 1.0)


def portfolio_backtest(
    pred_df: pd.DataFrame,
    fwd_df:  pd.DataFrame,
    kospi:   pd.DataFrame,
    *,
    top_k:     int = DEFAULT_TOP_K,
    rebalance: int = REBALANCE_DAYS,
) -> dict:
    """
    매 rebalance 거래일마다 top_k 매수, period_return = mean(fwd_return_20d).
    return: portfolio metrics dict.
    """
    pred_df = pred_df.merge(fwd_df, on=["date", "ticker"], how="inner")

    trading_dates = sorted(pred_df["date"].unique())
    starts = rebalance_dates([pd.Timestamp(d) for d in trading_dates], rebalance)
    log(f"  rebalance starts: {len(starts)} (first {starts[0].date()}, last {starts[-1].date()})")

    period_returns: list[float] = []
    period_alphas:  list[float] = []
    period_hit:     list[bool]  = []
    n_picks: list[int] = []

    for s in starts:
        # period 끝일 = s + rebalance 영업일 - 1.
        idx = trading_dates.index(np.datetime64(s.date()))
        end_idx = min(idx + rebalance - 1, len(trading_dates) - 1)
        end_d = pd.Timestamp(trading_dates[end_idx])

        cohort = pred_df[pred_df["date"] == s]
        if cohort.empty:
            continue
        cohort = cohort.sort_values("rank_in_date").head(top_k)
        if cohort.empty:
            continue

        port_ret = float(cohort["fwd_return_20d"].mean())
        kospi_ret = kospi_period_return(kospi, s, end_d)
        alpha = port_ret - kospi_ret if np.isfinite(kospi_ret) else float("nan")

        period_returns.append(port_ret)
        period_alphas.append(alpha)
        period_hit.append(port_ret > 0)
        n_picks.append(int(len(cohort)))

    arr = np.asarray(period_returns, dtype=float)
    if len(arr) < 2:
        return {"error": "insufficient periods", "n_periods": len(arr)}

    cum_ret = float(np.prod(1.0 + arr) - 1.0)
    cum_kospi = 1.0
    for s in starts:
        idx = trading_dates.index(np.datetime64(s.date()))
        end_idx = min(idx + rebalance - 1, len(trading_dates) - 1)
        end_d = pd.Timestamp(trading_dates[end_idx])
        kr = kospi_period_return(kospi, s, end_d)
        if np.isfinite(kr):
            cum_kospi *= (1.0 + kr)
    cum_kospi -= 1.0

    mu = float(arr.mean())
    sd = float(arr.std(ddof=1)) if len(arr) > 1 else float("nan")
    sharpe = (mu / sd) * np.sqrt(PERIODS_PER_YEAR) if sd > 0 else float("nan")

    # Maximum Drawdown over compounded equity curve.
    equity = np.cumprod(1.0 + arr)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    mdd = float(dd.min())

    hit_rate = float(np.mean(period_hit)) if period_hit else float("nan")
    cum_alpha = cum_ret - cum_kospi

    # PSR: Probability that true Sharpe > 0 (López de Prado).
    # PSR = Φ((SR − 0)·sqrt(n−1) / sqrt(1 − γ3·SR + (γ4−1)/4·SR²))
    from math import erf, sqrt
    def _norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + erf(x / sqrt(2.0)))

    n = len(arr)
    if n >= 4 and sd > 0:
        # 표본 skew·kurt.
        gamma3 = float(((arr - mu) ** 3).mean() / sd**3)
        gamma4 = float(((arr - mu) ** 4).mean() / sd**4)
        denom = max(1e-12, 1 - gamma3 * sharpe / np.sqrt(PERIODS_PER_YEAR)
                            + (gamma4 - 1) / 4 * (sharpe / np.sqrt(PERIODS_PER_YEAR)) ** 2)
        psr = float(_norm_cdf((sharpe / np.sqrt(PERIODS_PER_YEAR)) * np.sqrt(n - 1) / np.sqrt(denom)))
    else:
        gamma3 = gamma4 = float("nan")
        psr = float("nan")

    # DSR (n_trials=1) — 단일 trial 가정.
    dsr_n1 = psr

    return {
        "n_periods":         int(n),
        "top_k":             int(top_k),
        "rebalance_days":    int(rebalance),
        "periods_per_year":  PERIODS_PER_YEAR,
        "mean_picks":        float(np.mean(n_picks)),
        "sharpe_annualized": float(sharpe) if np.isfinite(sharpe) else None,
        "cumulative_return": cum_ret,
        "cumulative_kospi":  cum_kospi,
        "cumulative_alpha":  cum_alpha,
        "max_drawdown":      mdd,
        "hit_rate":          hit_rate,
        "psr_threshold_0":   psr if np.isfinite(psr) else None,
        "dsr_n1":            dsr_n1 if np.isfinite(dsr_n1) else None,
        "skewness":          gamma3 if np.isfinite(gamma3) else None,
        "kurtosis":          gamma4 if np.isfinite(gamma4) else None,
        "period_returns":    [float(x) for x in arr.tolist()],
        "period_alphas":     [float(x) if np.isfinite(x) else None for x in period_alphas],
    }


# ── 3) 박제 ─────────────────────────────────────────────────────────────────

def archive_holdout(payload: dict, variant: str, force: bool) -> Path:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = ARCHIVE_ROOT / f"holdout_2026_q1_q2_{variant}.json"
    if out_path.exists() and not force:
        raise FileExistsError(f"[REFUSED] 이미 박제: {out_path}. --force 명시 시 덮어쓰기.")
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


# ── 메인 ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="W7A — v11 holdout 추론·backtest·박제")
    parser.add_argument("--variant", default="a_prime",
                        help="모델 디렉터리 접미사 (예: a, a_prime, b).")
    parser.add_argument("--top-k",     type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--rebalance", type=int, default=REBALANCE_DAYS)
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--force",     action="store_true")
    args = parser.parse_args()

    log("=== infer_v11_holdout (W7A Step 2) ===")
    log(f"  variant: v11{args.variant}")
    log(f"  top_k:   {args.top_k}")

    booster, feature_cols, train_meta = load_model(args.variant)
    log(f"  features (model): {len(feature_cols)}")

    log("  predicting holdout …")
    pred_df = predict_holdout(booster, feature_cols)

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        log("  loading fwd_return_20d (multi_labels) …")
        fwd_df = load_fwd_returns(con)
        log(f"    rows: {len(fwd_df):,}")

    finally:
        con.close()

    log("  loading KOSPI …")
    kospi = load_kospi_close()
    log(f"    rows: {len(kospi):,}")

    log("  portfolio backtest …")
    metrics = portfolio_backtest(pred_df, fwd_df, kospi,
                                 top_k=args.top_k, rebalance=args.rebalance)

    payload = {
        "experiment":         "W7A — v11 holdout (2026 Q1·Q2) vs v9",
        "model_version":      f"v11{args.variant}",
        "target_label":       train_meta.get("target_label"),
        "use_embeddings":     train_meta.get("use_embeddings"),
        "n_train_features":   train_meta.get("n_features"),
        "n_train_rows":       train_meta.get("n_train_rows"),
        "valid_ndcg@10":      train_meta.get("valid_ndcg@10"),
        "holdout_start":      HOLDOUT_START,
        "holdout_end":        HOLDOUT_END,
        "computed_at":        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metrics":            metrics,
    }

    log("=== holdout metrics ===")
    for k in ["sharpe_annualized", "cumulative_return", "cumulative_kospi",
              "cumulative_alpha", "max_drawdown", "hit_rate",
              "psr_threshold_0", "dsr_n1"]:
        v = metrics.get(k)
        log(f"  {k}: {v}")

    if args.dry_run:
        log("--- dry-run (박제 생략) ---")
        return 0

    out_path = archive_holdout(payload, args.variant, args.force)
    log(f"  archived → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
