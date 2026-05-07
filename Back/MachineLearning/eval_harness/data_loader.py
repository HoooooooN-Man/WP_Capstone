"""
eval_harness/data_loader.py
===========================
Tier 1.2 — 평가 하네스용 데이터 로더.

`holdout_evaluator.load_holdout_data` 와 동일 베이스에서 *슬라이스 키* 컬럼을
추가로 만든다:
  - year         : YYYY 문자열
  - sector       : scores.sector
  - cap_quartile : 시장 가치(market_cap) 4분위 라벨 (Q1=소형 ~ Q4=대형)
  - regime       : KOSPI 005930 의 20일 MA 위/아래 (Up / Down)

라벨링·forward window 정책은 holdout_evaluator 와 동일 (label ≥ +5%, fwd=20일).
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import pandas as pd


LABEL_THRESHOLD = 0.05
FORWARD_DAYS = 20


@dataclass
class EvalDataset:
    """평가 하네스가 슬라이서·메트릭에 넘기는 표준 자료구조."""
    rows: pd.DataFrame                # 행 단위(date_int, ticker) 평가 데이터
    period_returns: pd.DataFrame      # non-overlapping 20거래일 period 시계열
    bench_returns: pd.DataFrame       # KOSPI 프록시 (date_int → bench_return)
    rebalance_dates: list[int]        # period 시계열의 시작 날짜


def _load_base(con: duckdb.DuckDBPyConnection, model_version: str) -> pd.DataFrame:
    """scores + prices(today + fwd) join → 행별 prob/label/sector 등."""
    df = con.execute("""
        SELECT
            CAST(s.date AS VARCHAR)                          AS date_str,
            CAST(strftime(CAST(s.date AS DATE), '%Y%m%d') AS BIGINT) AS date_int,
            s.ticker,
            s.sector,
            CAST(s.prob_ensemble AS DOUBLE)                  AS prob,
            CAST(s.score AS DOUBLE)                          AS score,
            s.tier,
            CAST(p.close AS DOUBLE)                          AS close_today,
            CAST(p.market_cap AS DOUBLE)                     AS market_cap
        FROM scores s
        JOIN prices p
          ON p.ticker = s.ticker
         AND p.date   = CAST(strftime(CAST(s.date AS DATE), '%Y%m%d') AS BIGINT)
        WHERE s.model_version = ?
        ORDER BY s.ticker, s.date
    """, [model_version]).fetchdf()
    return df


def _attach_forward(df: pd.DataFrame) -> pd.DataFrame:
    """ticker 별로 close 를 FORWARD_DAYS 만큼 shift 해 forward return·label 만든다."""
    df = df.sort_values(["ticker", "date_int"]).reset_index(drop=True)
    df["close_fwd"] = df.groupby("ticker")["close_today"].shift(-FORWARD_DAYS)
    df = df.dropna(subset=["close_fwd"]).copy()
    df["fwd_return"] = (df["close_fwd"] - df["close_today"]) / df["close_today"]
    df["label"] = (df["fwd_return"] >= LABEL_THRESHOLD).astype(int)
    df["year"] = df["date_str"].str.slice(0, 4)
    return df


def _attach_cap_quartile(df: pd.DataFrame) -> pd.DataFrame:
    """
    market_cap 4분위 라벨. *날짜별로* 분위를 잡으면 시간 흐름에 안정적.
    market_cap 누락 행은 'Unknown' 으로 분류.
    """
    df = df.copy()
    if "market_cap" not in df.columns or df["market_cap"].isna().all():
        df["cap_quartile"] = "Unknown"
        return df

    def _per_date(group: pd.DataFrame) -> pd.Series:
        mc = group["market_cap"]
        if mc.notna().sum() < 4:
            return pd.Series(["Unknown"] * len(group), index=group.index)
        try:
            q = pd.qcut(mc, q=4, labels=["Q1_small", "Q2", "Q3", "Q4_large"], duplicates="drop")
            return q.astype(str).fillna("Unknown")
        except Exception:
            return pd.Series(["Unknown"] * len(group), index=group.index)

    df["cap_quartile"] = (
        df.groupby("date_int", group_keys=False)
        .apply(_per_date)
        .astype(str)
    )
    return df


def _attach_regime(df: pd.DataFrame, con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    각 행의 date_int 기준 KOSPI 프록시(005930) 의 20일 MA 위/아래로 regime 라벨.
    Up = KOSPI close ≥ MA20, Down = below.
    """
    bench = con.execute("""
        SELECT date AS date_int, CAST(close AS DOUBLE) AS close
        FROM prices
        WHERE ticker = '005930'
        ORDER BY date
    """).fetchdf()
    bench = bench.sort_values("date_int").reset_index(drop=True)
    bench["ma20"] = bench["close"].rolling(window=20, min_periods=5).mean()
    bench["regime"] = np.where(bench["close"] >= bench["ma20"], "Up", "Down")

    df = df.merge(bench[["date_int", "regime"]], on="date_int", how="left")
    df["regime"] = df["regime"].fillna("Unknown")
    return df


# ── period 시계열 (non-overlapping rebalance) ─────────────────────────────────

def _build_period_series(
    df: pd.DataFrame, bench: pd.DataFrame, fwd: int = FORWARD_DAYS,
) -> tuple[pd.DataFrame, list[int]]:
    """
    holdout_evaluator 와 동일한 정책: 평가 가능한 거래일을 fwd 간격으로 sample.
    Tier A 종목 평균 forward return 을 strategy 시계열로 사용.
    """
    eval_dates = sorted(df["date_int"].unique())
    rebalance_dates = eval_dates[::fwd]
    tier_a = df[df["tier"] == "A"]

    rows = []
    for rd in rebalance_dates:
        picks = tier_a[tier_a["date_int"] == rd]
        if picks.empty:
            continue
        b = bench[bench["date_int"] == rd]
        if b.empty:
            continue
        rows.append({
            "date_int":     int(rd),
            "n_picks":      int(len(picks)),
            "strat_return": float(picks["fwd_return"].mean()),
            "bench_return": float(b["bench_return"].iloc[0]),
        })
    period_df = pd.DataFrame(rows)
    if not period_df.empty:
        period_df["alpha"] = period_df["strat_return"] - period_df["bench_return"]
    return period_df, rebalance_dates


def _load_bench_returns(con: duckdb.DuckDBPyConnection, fwd: int = FORWARD_DAYS) -> pd.DataFrame:
    df = con.execute("""
        SELECT date AS date_int, CAST(close AS DOUBLE) AS close
        FROM prices
        WHERE ticker = '005930'
        ORDER BY date
    """).fetchdf()
    df = df.sort_values("date_int").reset_index(drop=True)
    df["close_fwd"] = df["close"].shift(-fwd)
    df = df.dropna(subset=["close_fwd"]).copy()
    df["bench_return"] = (df["close_fwd"] - df["close"]) / df["close"]
    return df[["date_int", "bench_return"]]


# ── public ────────────────────────────────────────────────────────────────────

def load_eval_dataset(
    db_path: str,
    model_version: str = "v9",
) -> EvalDataset:
    """평가 하네스 진입점이 호출. DuckDB 한 번만 열고 모든 슬라이스 키 부착."""
    con = duckdb.connect(db_path, read_only=True)
    try:
        base = _load_base(con, model_version)
        if base.empty:
            return EvalDataset(
                rows=base, period_returns=pd.DataFrame(),
                bench_returns=pd.DataFrame(), rebalance_dates=[],
            )
        rows = _attach_forward(base)
        rows = _attach_cap_quartile(rows)
        rows = _attach_regime(rows, con)
        bench = _load_bench_returns(con)
        period_df, rebal = _build_period_series(rows, bench)
        return EvalDataset(
            rows=rows,
            period_returns=period_df,
            bench_returns=bench,
            rebalance_dates=rebal,
        )
    finally:
        con.close()
