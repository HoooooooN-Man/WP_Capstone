"""
compute_multi_labels.py
=======================
W4 진입점 — 5 멀티 라벨 raw 값 일괄 계산 → DuckDB `multi_labels` 적재.

흐름:
  1. DuckDB scores 에서 (date, ticker) 쌍 추출 (또는 prices 의 모든 거래일).
  2. 각 ticker 의 close 시계열 + KOSPI 프록시(005930) close 시계열 로드.
  3. multi_labels.compute_all_labels 호출 → fwd_return·alpha·sharpe 5컬럼.
  4. (date, ticker) PK 로 UPSERT — idempotent.

저장 위치: 캡스톤 v9 가 쓰는 같은 DuckDB (market_data.duckdb) 의 `multi_labels` 테이블.
이유: 다운스트림 W6 LambdaRank 가 학습 시 *features × labels* 를 join. 같은 DB 가 자연.

사용:
  py compute_multi_labels.py                       # 전체 ticker
  py compute_multi_labels.py --max-tickers 50      # 빠른 시연
  py compute_multi_labels.py --dry-run             # 적재 생략
  py compute_multi_labels.py --start 2024-01-01    # 범위 한정
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from multi_labels import compute_all_labels


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data\project_data"))
DUCKDB_PATH   = Path(os.getenv("DUCKDB_PATH", str(CAPSTONE_ROOT / "db" / "market_data.duckdb")))
BENCHMARK_TICKER = "005930"   # KOSPI 프록시 (홀드아웃·캡스톤 동일)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 스키마 ──────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS multi_labels (
    date           BIGINT,
    ticker         VARCHAR,
    fwd_return_5d  REAL,
    fwd_return_20d REAL,
    fwd_return_60d REAL,
    alpha_5d       REAL,
    alpha_20d      REAL,
    alpha_60d      REAL,
    sharpe_20d     REAL,
    computed_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, ticker)
)
"""


def ensure_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(CREATE_TABLE_SQL)


# ── 데이터 로딩 ─────────────────────────────────────────────────────────────

def load_benchmark_series(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """KOSPI 프록시 종가 시계열 (date, close)."""
    return con.execute(
        f"SELECT date, close FROM prices WHERE ticker = '{BENCHMARK_TICKER}' ORDER BY date"
    ).fetchdf()


def list_tickers(
    con: duckdb.DuckDBPyConnection,
    *,
    max_tickers: int = 0,
    exclude_benchmark: bool = False,
) -> list[str]:
    sql = "SELECT DISTINCT ticker FROM prices"
    if exclude_benchmark:
        sql += f" WHERE ticker <> '{BENCHMARK_TICKER}'"
    sql += " ORDER BY ticker"
    if max_tickers > 0:
        sql += f" LIMIT {int(max_tickers)}"
    return [r[0] for r in con.execute(sql).fetchall()]


def load_close_series(
    con: duckdb.DuckDBPyConnection,
    ticker: str,
    *,
    start_yyyymmdd: Optional[int] = None,
    end_yyyymmdd:   Optional[int] = None,
) -> pd.DataFrame:
    where = ["ticker = ?"]
    params: list = [ticker]
    if start_yyyymmdd is not None:
        where.append("date >= ?")
        params.append(start_yyyymmdd)
    if end_yyyymmdd is not None:
        where.append("date <= ?")
        params.append(end_yyyymmdd)
    sql = f"SELECT date, close FROM prices WHERE {' AND '.join(where)} ORDER BY date"
    return con.execute(sql, params).fetchdf()


def align_benchmark(stock_df: pd.DataFrame, bench_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    stock·benchmark 를 *공통 거래일* 로 inner-join. 정렬된 (dates, stock_close, bench_close).
    """
    merged = stock_df.merge(bench_df, on="date", how="inner", suffixes=("", "_bench"))
    merged = merged.sort_values("date").reset_index(drop=True)
    if merged.empty:
        return np.array([]), np.array([]), np.array([])
    return (
        merged["date"].values.astype(np.int64),
        merged["close"].values.astype(float),
        merged["close_bench"].values.astype(float),
    )


# ── UPSERT ──────────────────────────────────────────────────────────────────

UPSERT_SQL = """
INSERT INTO multi_labels (
    date, ticker,
    fwd_return_5d, fwd_return_20d, fwd_return_60d,
    alpha_5d,      alpha_20d,      alpha_60d,
    sharpe_20d
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (date, ticker) DO UPDATE SET
    fwd_return_5d  = EXCLUDED.fwd_return_5d,
    fwd_return_20d = EXCLUDED.fwd_return_20d,
    fwd_return_60d = EXCLUDED.fwd_return_60d,
    alpha_5d       = EXCLUDED.alpha_5d,
    alpha_20d      = EXCLUDED.alpha_20d,
    alpha_60d      = EXCLUDED.alpha_60d,
    sharpe_20d     = EXCLUDED.sharpe_20d,
    computed_at    = NOW()
"""


def _to_py_float(v) -> Optional[float]:
    """numpy NaN 또는 미정의 → None (DuckDB NULL)."""
    if v is None:
        return None
    f = float(v)
    if f != f:   # NaN
        return None
    return f


def upsert_labels(
    con: duckdb.DuckDBPyConnection,
    ticker: str,
    dates: np.ndarray,
    labels: dict[str, np.ndarray],
) -> int:
    """
    DataFrame register + INSERT FROM SELECT — DuckDB vectorized.
    executemany row-by-row 대비 50~100배 빠름.
    """
    n = len(dates)
    if n == 0:
        return 0
    df = pd.DataFrame({
        "date":           np.asarray(dates, dtype=np.int64),
        "ticker":         np.full(n, ticker, dtype=object),
        "fwd_return_5d":  labels["fwd_return_5d"].astype(np.float32),
        "fwd_return_20d": labels["fwd_return_20d"].astype(np.float32),
        "fwd_return_60d": labels["fwd_return_60d"].astype(np.float32),
        "alpha_5d":       labels["alpha_5d"].astype(np.float32),
        "alpha_20d":      labels["alpha_20d"].astype(np.float32),
        "alpha_60d":      labels["alpha_60d"].astype(np.float32),
        "sharpe_20d":     labels["sharpe_20d"].astype(np.float32),
    })
    con.register("upsert_df", df)
    con.execute("""
        INSERT INTO multi_labels
        SELECT date, ticker,
               fwd_return_5d, fwd_return_20d, fwd_return_60d,
               alpha_5d,      alpha_20d,      alpha_60d,
               sharpe_20d,    NOW()                              AS computed_at
        FROM upsert_df
        ON CONFLICT (date, ticker) DO UPDATE SET
            fwd_return_5d  = EXCLUDED.fwd_return_5d,
            fwd_return_20d = EXCLUDED.fwd_return_20d,
            fwd_return_60d = EXCLUDED.fwd_return_60d,
            alpha_5d       = EXCLUDED.alpha_5d,
            alpha_20d      = EXCLUDED.alpha_20d,
            alpha_60d      = EXCLUDED.alpha_60d,
            sharpe_20d     = EXCLUDED.sharpe_20d,
            computed_at    = NOW()
    """)
    con.unregister("upsert_df")
    return n


# ── 메인 파이프라인 ────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="W4 — 5 멀티 라벨 일괄 계산·적재")
    parser.add_argument("--max-tickers", type=int, default=0,
                        help="0 = 전체. 빠른 시연 50.")
    parser.add_argument("--start", default=None, help="YYYY-MM-DD (선택, 시계열 cutoff)")
    parser.add_argument("--end",   default=None, help="YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DUCKDB_PATH.exists():
        log(f"[ERROR] DuckDB 없음: {DUCKDB_PATH}")
        return 1

    log("=== compute_multi_labels (W4) ===")
    log(f"  DuckDB: {DUCKDB_PATH}")
    log(f"  benchmark: {BENCHMARK_TICKER}")
    if args.max_tickers > 0:
        log(f"  max_tickers: {args.max_tickers}")
    if args.dry_run:
        log("  DRY-RUN — 적재 생략")

    start_int = int(args.start.replace("-", "")) if args.start else None
    end_int   = int(args.end.replace("-", ""))   if args.end   else None

    # *읽기·쓰기 동시* 필요 (CREATE TABLE + INSERT). read_only=False.
    con = duckdb.connect(str(DUCKDB_PATH))
    try:
        ensure_table(con)
        bench_df = load_benchmark_series(con)
        if bench_df.empty:
            log(f"[ERROR] benchmark {BENCHMARK_TICKER} prices 부재")
            return 2
        log(f"  benchmark days: {len(bench_df)}")

        tickers = list_tickers(con, max_tickers=args.max_tickers, exclude_benchmark=False)
        log(f"  tickers to process: {len(tickers):,}")

        total_rows = 0
        skipped = 0
        for i, t in enumerate(tickers, 1):
            stock_df = load_close_series(con, t, start_yyyymmdd=start_int, end_yyyymmdd=end_int)
            if stock_df.empty or len(stock_df) < 65:    # sharpe_20d + 여유.
                skipped += 1
                continue
            dates, stock_close, bench_close = align_benchmark(stock_df, bench_df)
            if dates.size == 0:
                skipped += 1
                continue
            labels = compute_all_labels(stock_close, bench_close)
            if not args.dry_run:
                total_rows += upsert_labels(con, t, dates, labels)
            else:
                total_rows += len(dates)
            if i % 200 == 0:
                log(f"    progress: {i}/{len(tickers)} (rows so far: {total_rows:,})")

        log(f"  Done. tickers processed: {len(tickers) - skipped} / skipped: {skipped}")
        log(f"  rows {'would-be ' if args.dry_run else ''}upserted: {total_rows:,}")
    finally:
        con.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
