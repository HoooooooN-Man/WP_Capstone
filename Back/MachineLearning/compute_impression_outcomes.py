"""
compute_impression_outcomes.py
==============================
W1E — 매일 자정 cron 실행. shown_at + N거래일 후 실제 수익률을 계산해
PostgreSQL `impression_outcomes` 에 적재.

데이터 소스:
  - PG `:8000` recommendation_impressions   (impression 메타·shown_tickers·shown_at)
  - DuckDB `:8001` prices                   (forward 가격 — 거래일 기준)

정책:
  - horizons = [5, 20, 60] 거래일.
  - 미적재 판정: LEFT JOIN impression_outcomes WHERE outcome IS NULL.
  - idempotent: (impression_id, horizon) PK → ON CONFLICT DO NOTHING.
  - 가격 부재 ticker 는 제외 — 가능한 것만 ticker_returns 에 채움. 모두 부재면 skip.

사용:
  py compute_impression_outcomes.py                    # full
  py compute_impression_outcomes.py --horizons 5 20    # 일부 horizon
  py compute_impression_outcomes.py --dry-run          # 적재 없이 미리보기
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import duckdb
import numpy as np


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data\project_data"))
DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", str(CAPSTONE_ROOT / "db" / "market_data.duckdb")))

PG_URL = os.getenv(
    "EVENTS_PG_URL",
    "postgresql://postgres:postgres@localhost:5432/wp_capstone",
)

DEFAULT_HORIZONS = (5, 20, 60)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 순수 함수 — 단위 테스트 가능 ────────────────────────────────────────────

def compute_ticker_returns(
    shown_tickers: list[dict],
    forward_close_by_ticker: dict[str, Optional[float]],
    base_close_by_ticker: dict[str, Optional[float]],
) -> dict[str, float]:
    """
    shown_tickers 의 각 ticker 에 대해 (forward / base - 1) 수익률.
    base 또는 forward 가 None 이거나 base ≤ 0 인 ticker 는 결과에서 제외.

    Parameters
    ----------
    shown_tickers : [{ticker, rank, ...}]  — impression 의 노출 종목 목록
    forward_close_by_ticker : {ticker: close_at_t+horizon} — 미존재면 None
    base_close_by_ticker    : {ticker: close_at_shown_at}

    Returns
    -------
    {ticker: return_pct}  (소수, 0.03 = +3%)
    """
    out: dict[str, float] = {}
    for entry in shown_tickers:
        ticker = entry.get("ticker")
        if not ticker:
            continue
        base = base_close_by_ticker.get(ticker)
        fwd = forward_close_by_ticker.get(ticker)
        if base is None or fwd is None or base <= 0:
            continue
        out[ticker] = round(float(fwd / base - 1.0), 6)
    return out


# ── DuckDB — 거래일 기반 forward close ──────────────────────────────────────

def get_close_at_or_before(
    con: duckdb.DuckDBPyConnection,
    ticker: str,
    date_yyyymmdd: int,
) -> Optional[float]:
    """주어진 날짜의 close. 휴장이면 가장 가까운 *이전* 거래일 close."""
    row = con.execute("""
        SELECT close FROM prices
        WHERE ticker = ? AND date <= ?
        ORDER BY date DESC LIMIT 1
    """, [ticker, date_yyyymmdd]).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def get_close_after_n_trading_days(
    con: duckdb.DuckDBPyConnection,
    ticker: str,
    base_yyyymmdd: int,
    horizon_days: int,
) -> Optional[float]:
    """ticker 의 base 이후 N번째 거래일 close. 부재 시 None (아직 미래)."""
    row = con.execute("""
        SELECT close FROM (
            SELECT close, ROW_NUMBER() OVER (ORDER BY date) AS rn
            FROM prices
            WHERE ticker = ? AND date > ?
        ) WHERE rn = ?
    """, [ticker, base_yyyymmdd, horizon_days]).fetchone()
    return float(row[0]) if row and row[0] is not None else None


# ── PG — 미적재 impression 조회 + 적재 ─────────────────────────────────────

def fetch_pending_impressions(
    pg_engine, horizon: int,
) -> list[dict]:
    """
    horizon 만큼 거래일이 *물리적으로* 흘렀고 outcome 행이 아직 없는 impression.
    여기서는 horizon 거래일 ≈ 1.5 × calendar days 로 보수적 cutoff (주말·공휴일 감안).
    DuckDB 가 실제 거래일 존재 여부를 결정하므로 cutoff 는 *후보 추리기* 용.
    """
    from sqlalchemy import text
    cutoff_calendar_days = int(horizon * 1.5) + 5
    sql = text(f"""
        SELECT
            i.impression_id::text AS impression_id,
            i.shown_at,
            i.shown_tickers
        FROM recommendation_impressions i
        LEFT JOIN impression_outcomes o
          ON o.impression_id = i.impression_id
         AND o.outcome_horizon_days = :horizon
        WHERE o.impression_id IS NULL
          AND i.shown_at <= NOW() - (:cutoff || ' days')::INTERVAL
        ORDER BY i.shown_at ASC
        LIMIT 5000
    """)
    with pg_engine.connect() as conn:
        rows = conn.execute(
            sql, {"horizon": horizon, "cutoff": cutoff_calendar_days},
        ).mappings().all()
    return [dict(r) for r in rows]


def insert_outcomes(
    pg_engine,
    rows: list[tuple[str, int, dict]],
) -> int:
    """(impression_id, horizon, ticker_returns) 일괄 INSERT. ON CONFLICT DO NOTHING."""
    if not rows:
        return 0
    from sqlalchemy import text
    sql = text("""
        INSERT INTO impression_outcomes
            (impression_id, outcome_horizon_days, ticker_returns)
        VALUES (:imp_id, :horizon, CAST(:returns AS JSONB))
        ON CONFLICT (impression_id, outcome_horizon_days) DO NOTHING
    """)
    with pg_engine.begin() as conn:
        for imp_id, horizon, returns in rows:
            conn.execute(sql, {
                "imp_id":  imp_id,
                "horizon": horizon,
                "returns": json.dumps(returns),
            })
    return len(rows)


# ── 메인 파이프라인 ─────────────────────────────────────────────────────────

def process_horizon(
    pg_engine,
    duck_con: duckdb.DuckDBPyConnection,
    horizon: int,
    *,
    dry_run: bool,
) -> tuple[int, int]:
    """horizon 한 개 처리 → (처리한 impression 수, 적재한 outcome 수)."""
    pending = fetch_pending_impressions(pg_engine, horizon)
    log(f"  horizon={horizon}d: pending {len(pending)}")
    if not pending:
        return (0, 0)

    to_insert: list[tuple[str, int, dict]] = []
    skipped = 0

    for imp in pending:
        shown_at: datetime = imp["shown_at"]
        shown_tickers = imp["shown_tickers"] or []
        if not isinstance(shown_tickers, list) or not shown_tickers:
            skipped += 1
            continue

        base_yyyymmdd = int(shown_at.strftime("%Y%m%d"))

        base_close: dict[str, Optional[float]] = {}
        forward_close: dict[str, Optional[float]] = {}
        for entry in shown_tickers:
            ticker = entry.get("ticker") if isinstance(entry, dict) else None
            if not ticker:
                continue
            base_close[ticker]    = get_close_at_or_before(duck_con, ticker, base_yyyymmdd)
            forward_close[ticker] = get_close_after_n_trading_days(
                duck_con, ticker, base_yyyymmdd, horizon,
            )

        returns = compute_ticker_returns(shown_tickers, forward_close, base_close)
        if not returns:
            # forward 거래일이 아직 안 찼거나, 모든 ticker 가격 부재.
            skipped += 1
            continue

        to_insert.append((imp["impression_id"], horizon, returns))

    log(f"  → ready to insert: {len(to_insert)}  (skipped: {skipped})")

    if dry_run:
        for imp_id, h, ret in to_insert[:3]:
            print(f"    [dry-run] {imp_id[:8]} horizon={h} returns={list(ret.items())[:3]}")
        return (len(pending), len(to_insert))

    inserted = insert_outcomes(pg_engine, to_insert)
    return (len(pending), inserted)


def main() -> int:
    parser = argparse.ArgumentParser(description="W1E — impression outcomes cron")
    parser.add_argument("--horizons", type=int, nargs="+", default=list(DEFAULT_HORIZONS))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DUCKDB_PATH.exists():
        log(f"[ERROR] DuckDB 없음: {DUCKDB_PATH}")
        return 1

    try:
        from sqlalchemy import create_engine
        pg_engine = create_engine(PG_URL, future=True)
        with pg_engine.connect():
            pass
    except Exception as e:
        log(f"[ERROR] PostgreSQL 연결 실패 ({PG_URL}): {e}")
        return 2

    log("=== compute_impression_outcomes ===")
    log(f"  PG:     {PG_URL}")
    log(f"  DuckDB: {DUCKDB_PATH}")
    log(f"  horizons: {args.horizons}  dry_run: {args.dry_run}")

    duck_con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    total_pending = total_inserted = 0
    try:
        for h in args.horizons:
            p, i = process_horizon(pg_engine, duck_con, h, dry_run=args.dry_run)
            total_pending  += p
            total_inserted += i
    finally:
        duck_con.close()

    log(f"Done. pending={total_pending} inserted={total_inserted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
