"""
backfill_2026_05_15.py
======================
2026-05-15 데이터 백필 — audit 후속, 4건 일괄 처리.

1) H#23 — scores.name v9 100% NULL → seed.csv (preprocessing/seed.csv) 의 name 으로 백필
2) H#25 — prices 미조정 split jump 29건 → split_events_2026.csv 의 ret_pct 로 backward adjust
3) L#56 — prices 거래정지 플래그 → trading_halt_tickers_2026.csv 매칭하여 is_halt 컬럼 추가
4) H#18 + M#34 — market_indices 135d stale → macro_indicators.csv 의 KOSPI/SP500/NASDAQ 로 extend

실행 전제: 8001/8000 백엔드가 DuckDB lock 을 잡고 있으면 실패하므로 미리 종료.
운영 시 외에서 한 번만 돌리고 commit. DRY-RUN 모드는 --dry-run.
"""
from __future__ import annotations

import argparse
import contextlib
import os
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd

# cron 텔레메트리 (Back/MachineLearning/cron_telemetry.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from cron_telemetry import track_run as _track_run
except ImportError:
    @contextlib.contextmanager
    def _track_run(_step: str):
        class _H: rows = None
        yield _H()

# ── 경로 ──────────────────────────────────────────────────────────────────────
BASE = Path(r"E:\Capstone Data")
DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", str(BASE / "project_data" / "db" / "market_data.duckdb")))
SEED_CSV    = BASE / "project_data" / "preprocessing" / "seed.csv"
SPLIT_CSV   = BASE / "data_pipeline" / "split_events_2026.csv"
HALT_CSV    = BASE / "data_pipeline" / "trading_halt_tickers_2026.csv"
MACRO_CSV   = BASE / "data_pipeline" / "macro_indicators.csv"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 1) v9 scores.name backfill ───────────────────────────────────────────────

def backfill_v9_name(con: duckdb.DuckDBPyConnection, dry: bool) -> int:
    log("(1) v9 scores.name backfill — seed.csv → scores")
    if not SEED_CSV.exists():
        log(f"    ✗ seed.csv 없음: {SEED_CSV}")
        return 0
    seed = pd.read_csv(SEED_CSV, dtype={"ticker": str})
    if "ticker" not in seed.columns or "name" not in seed.columns:
        log(f"    ✗ seed.csv 컬럼 부족 — got: {list(seed.columns)}")
        return 0
    seed = seed[["ticker", "name"]].drop_duplicates("ticker")
    seed["ticker"] = seed["ticker"].str.zfill(6)

    before = con.execute(
        "SELECT COUNT(*) FROM scores WHERE model_version='v9' AND name IS NULL"
    ).fetchone()[0]
    log(f"    before: name NULL = {before:,}")

    if dry:
        log("    [DRY] skipping write")
        return before

    con.register("seed_df", seed)
    con.execute("""
        UPDATE scores
           SET name = seed_df.name
          FROM seed_df
         WHERE scores.model_version = 'v9'
           AND scores.ticker = seed_df.ticker
           AND scores.name IS NULL
    """)
    con.unregister("seed_df")
    after = con.execute(
        "SELECT COUNT(*) FROM scores WHERE model_version='v9' AND name IS NULL"
    ).fetchone()[0]
    log(f"    after:  name NULL = {after:,}  (filled {before - after:,})")
    return before - after


# ── 2) prices split backward adjustment ───────────────────────────────────────

def backfill_split_adjust(con: duckdb.DuckDBPyConnection, dry: bool) -> int:
    log("(2) prices split backward adjust — split_events_2026.csv")
    if not SPLIT_CSV.exists():
        log(f"    ✗ split_events_2026.csv 없음: {SPLIT_CSV}")
        return 0

    events = pd.read_csv(SPLIT_CSV, dtype={"ticker": str})
    # SPLIT(주식분할): ret_pct < 0, vol_ratio > 1 — 가격이 1/N 로 줄음 → 분할 전 가격에 factor 곱해 정합
    # MERGE(합병/액면병합): ret_pct > 0 — 보통 거래정지/재상장 이슈, 가격 비교 무의미 → 건너뜀
    events = events[events["event_type"] == "SPLIT"].copy()
    if events.empty:
        log("    no SPLIT events — skip")
        return 0

    events["ticker"] = events["ticker"].str.zfill(6)
    # 분할 전 prices 의 close 를 (1 - |ret_pct|/100) 만큼 곱해 분할 후 단위로 정합.
    # 예: ret_pct=-43.4 → factor = (1 + ret_pct/100) = 0.566 ≈ 1/1.765 (액면분할 2:1.13 등)
    events["factor"] = 1.0 + events["ret_pct"] / 100.0
    events["event_date_int"] = events["date"].str.replace("-", "").astype(int)

    adjusted_rows = 0
    for _, ev in events.iterrows():
        t, dt, f = ev["ticker"], int(ev["event_date_int"]), float(ev["factor"])
        if f <= 0 or f >= 1.0:
            continue  # 비정상 분할 비율 — 보수적 skip
        if dry:
            n = con.execute(
                "SELECT COUNT(*) FROM prices WHERE ticker=? AND date < ?",
                [t, dt],
            ).fetchone()[0]
            log(f"    [DRY] {t} on {dt}: would adjust {n:,} rows × {f:.4f}")
            adjusted_rows += n
            continue
        # OHLCV 동시 조정 — close/open/high/low 모두 factor 배, volume 은 (1/factor)
        cur = con.execute(
            """
            UPDATE prices
               SET close  = close  * ?,
                   open   = open   * ?,
                   high   = high   * ?,
                   low    = low    * ?,
                   volume = CAST(volume / ? AS BIGINT)
             WHERE ticker = ?
               AND date   < ?
            """,
            [f, f, f, f, f, t, dt],
        )
        # DuckDB UPDATE 는 rowcount 제공 안 함 — 사전 SELECT 으로 추정 가능하지만 비용 회피
        n = con.execute(
            "SELECT COUNT(*) FROM prices WHERE ticker=? AND date < ?",
            [t, dt],
        ).fetchone()[0]
        adjusted_rows += n
    log(f"    adjusted: {adjusted_rows:,} pre-split rows across {len(events)} SPLIT events")
    return adjusted_rows


# ── 3) prices 거래정지 플래그 ──────────────────────────────────────────────────

def backfill_halt_flag(con: duckdb.DuckDBPyConnection, dry: bool) -> int:
    """거래정지 종목 별도 테이블로 적재.

    prices 테이블에 ALTER 가 안 되는 환경(인덱스/외부참조 의존)을 고려해 별도
    `trading_halts(ticker, halted_at)` 테이블을 만들고, 서비스 측에서 JOIN.
    """
    log("(3) trading_halts table — trading_halt_tickers_2026.csv")
    if not HALT_CSV.exists():
        log(f"    ✗ halt csv 없음: {HALT_CSV}")
        return 0

    halts = pd.read_csv(HALT_CSV, dtype={"ticker": str})
    halts["ticker"] = halts["ticker"].str.zfill(6)
    halts = halts.drop_duplicates(subset=["ticker"])
    log(f"    halt list: {len(halts):,} tickers")

    if dry:
        log("    [DRY] would CREATE TABLE IF NOT EXISTS trading_halts(ticker VARCHAR PRIMARY KEY, halted_at TIMESTAMP DEFAULT now())")
        log(f"    [DRY] would INSERT {len(halts):,} rows")
        return 0

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS trading_halts (
            ticker     VARCHAR PRIMARY KEY,
            halted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            note       VARCHAR
        )
        """
    )
    # 기존 행은 유지하고 누락된 ticker 만 추가.
    con.register("halt_df", halts[["ticker"]])
    con.execute(
        """
        INSERT INTO trading_halts (ticker)
        SELECT ticker FROM halt_df
        WHERE ticker NOT IN (SELECT ticker FROM trading_halts)
        """
    )
    con.unregister("halt_df")
    total = con.execute("SELECT COUNT(*) FROM trading_halts").fetchone()[0]
    log(f"    + trading_halts rows: {total:,}")
    return total


# ── 4) market_indices extend ─────────────────────────────────────────────────

def backfill_market_indices(con: duckdb.DuckDBPyConnection, dry: bool) -> int:
    log("(4) market_indices extend — macro_indicators.csv")
    if not MACRO_CSV.exists():
        log(f"    ✗ macro_indicators.csv 없음: {MACRO_CSV}")
        return 0

    df = pd.read_csv(MACRO_CSV)
    if "date" not in df.columns or "KOSPI" not in df.columns:
        log(f"    ✗ 필수 컬럼 부족 — got: {list(df.columns)[:5]}...")
        return 0

    # macro_indicators.csv 의 date 는 ISO("YYYY-MM-DD"), market_indices.date 는 DATE 타입
    df["date_iso"] = df["date"]
    df = df.dropna(subset=["KOSPI"])
    df["date"] = pd.to_datetime(df["date_iso"])  # pandas Timestamp 통일

    # 기존 market_indices 의 최신 날짜 이후만 insert.
    cur_max = con.execute("SELECT MAX(date) FROM market_indices").fetchone()[0]
    log(f"    market_indices.MAX(date) = {cur_max}")
    if cur_max is not None:
        cur_max_ts = pd.Timestamp(cur_max)
        df = df[df["date"] > cur_max_ts]
    log(f"    rows to insert: {len(df):,}")
    if df.empty:
        return 0
    if dry:
        log(f"    [DRY] would insert {len(df):,} rows ({df['date'].min()} ~ {df['date'].max()})")
        return len(df)

    # market_indices 실제 스키마:
    #   date, exchange_rate, kospi_open/high/low/close, kosdaq_open/high/low/close
    # macro_indicators.csv 는 daily close 만 제공 (OHLC 없음, kosdaq 없음, fx 없음).
    # → kospi_close 만 채우고 나머지는 NULL 로 insert. 운영용 일배치가 복구되면
    #   추후 OHLC + kosdaq + exchange_rate 가 모두 채워질 예정.
    payload = pd.DataFrame({
        "date":          df["date"].values,
        "exchange_rate": [None] * len(df),
        "kospi_open":    [None] * len(df),
        "kospi_high":    [None] * len(df),
        "kospi_low":     [None] * len(df),
        "kospi_close":   df["KOSPI"].values,
        "kosdaq_open":   [None] * len(df),
        "kosdaq_high":   [None] * len(df),
        "kosdaq_low":    [None] * len(df),
        "kosdaq_close":  [None] * len(df),
    })
    con.register("ins_df", payload)
    con.execute(
        """
        INSERT INTO market_indices
            (date, exchange_rate,
             kospi_open, kospi_high, kospi_low, kospi_close,
             kosdaq_open, kosdaq_high, kosdaq_low, kosdaq_close)
        SELECT date, exchange_rate,
               kospi_open, kospi_high, kospi_low, kospi_close,
               kosdaq_open, kosdaq_high, kosdaq_low, kosdaq_close
        FROM ins_df
        """
    )
    con.unregister("ins_df")
    new_max = con.execute("SELECT MAX(date) FROM market_indices").fetchone()[0]
    log(f"    + inserted {len(payload):,} rows (kospi_close only). new MAX(date) = {new_max}")
    return len(payload)


# ── 6) fx (USD/KRW) 백필 — yfinance ───────────────────────────────────────────

def backfill_fx(con: duckdb.DuckDBPyConnection, dry: bool) -> int:
    """fx 테이블 USD/KRW 시계열 갱신.

    소스: yfinance (Yahoo KRW=X) — 무료, 키 없음, 일별 close.
    fx 테이블 스키마: (date VARCHAR, usdkrw DOUBLE).
    기존 max(date) 이후만 INSERT — 중복 방지.
    """
    log("(6) fx USD/KRW backfill — yfinance KRW=X")
    try:
        import yfinance as yf
    except ImportError:
        log("    ✗ yfinance 미설치 — `pip install yfinance` 후 재시도")
        return 0

    cur_max = con.execute("SELECT MAX(date) FROM fx").fetchone()[0]
    log(f"    fx.MAX(date) = {cur_max}")

    # cur_max 다음날 ~ 오늘. 여유 두고 95일 잡아 일/주말 누락 흡수.
    import pandas as _pd
    from datetime import timedelta as _td
    start = (_pd.to_datetime(cur_max) + _td(days=1)).strftime("%Y-%m-%d") if cur_max else "2016-01-01"

    log(f"    fetching KRW=X since {start}...")
    hist = yf.Ticker("KRW=X").history(start=start, auto_adjust=False)
    if hist is None or hist.empty:
        log("    no new fx rows from Yahoo")
        return 0
    hist = hist[["Close"]].rename(columns={"Close": "usdkrw"})
    hist = hist.reset_index()
    hist["date"] = _pd.to_datetime(hist["Date"]).dt.strftime("%Y-%m-%d")
    payload = hist[["date", "usdkrw"]].dropna()
    # 기존 일치 행 제거 (혹시 모를 중복)
    if cur_max:
        payload = payload[payload["date"] > str(cur_max)]
    log(f"    rows to insert: {len(payload):,}")
    if payload.empty:
        return 0
    if dry:
        log(f"    [DRY] would insert {len(payload):,} rows ({payload['date'].min()} ~ {payload['date'].max()})")
        return len(payload)

    con.register("fx_df", payload)
    con.execute("INSERT INTO fx (date, usdkrw) SELECT date, usdkrw FROM fx_df")
    con.unregister("fx_df")
    new_max = con.execute("SELECT MAX(date) FROM fx").fetchone()[0]
    log(f"    + inserted {len(payload):,} rows. new MAX(date) = {new_max}")
    return len(payload)


# ── 5) finance 2026-Q1 skeleton row 삭제 ─────────────────────────────────────

def purge_finance_skeletons(con: duckdb.DuckDBPyConnection, dry: bool) -> int:
    """모든 키 필드가 NULL 인 분기 row 를 삭제.

    finance_2026_Q1.csv 가 2,365 ticker × NULL 인 skeleton 으로 적재되어,
    /api/v1/finance/{ticker} 가 "데이터 있음(스켈레톤)" 으로 위장됐다.
    완전히 비어 있는 행만 정리 — 부분적이라도 채워진 행은 보존.
    """
    log("(5) finance 2026-Q1 skeleton row purge")
    where = """
        year = 2026 AND quarter = 1
        AND revenue IS NULL AND op_profit IS NULL AND net_profit IS NULL
        AND eps IS NULL AND bps IS NULL AND per IS NULL AND pbr IS NULL
        AND dps IS NULL AND dividend_yield IS NULL
        AND roe IS NULL AND debt_ratio IS NULL
    """
    cnt = con.execute(f"SELECT COUNT(*) FROM finance WHERE {where}").fetchone()[0]
    log(f"    skeleton rows: {cnt:,}")
    if dry:
        log("    [DRY] would DELETE")
        return cnt
    con.execute(f"DELETE FROM finance WHERE {where}")
    after = con.execute("SELECT COUNT(*) FROM finance WHERE year=2026 AND quarter=1").fetchone()[0]
    log(f"    + remaining 2026-Q1 rows (real data only): {after:,}")
    return cnt


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="DB write 하지 않음")
    p.add_argument("--only", choices=["name", "split", "halt", "indices", "purge", "fx"], help="단일 단계만")
    args = p.parse_args()

    if not DUCKDB_PATH.exists():
        log(f"FATAL: DuckDB 파일 없음: {DUCKDB_PATH}")
        sys.exit(2)
    log(f"DuckDB: {DUCKDB_PATH}")
    log(f"mode:   {'DRY-RUN' if args.dry_run else 'WRITE'}")

    # cron 텔레메트리 — 각 단계마다 별도 run 으로 기록 (실패해도 다음 단계 진행 안 함).
    step_suffix = "_dry" if args.dry_run else ""
    name = f"backfill_2026_05_15{step_suffix}" if args.only is None else f"backfill_{args.only}{step_suffix}"
    with _track_run(name) as _run:
        con = duckdb.connect(str(DUCKDB_PATH), read_only=args.dry_run)
        total = 0
        try:
            if args.only in (None, "name"):
                total += backfill_v9_name(con, args.dry_run) or 0
            if args.only in (None, "split"):
                total += backfill_split_adjust(con, args.dry_run) or 0
            if args.only in (None, "halt"):
                total += backfill_halt_flag(con, args.dry_run) or 0
            if args.only in (None, "indices"):
                total += backfill_market_indices(con, args.dry_run) or 0
            if args.only in (None, "purge"):
                total += purge_finance_skeletons(con, args.dry_run) or 0
            if args.only in (None, "fx"):
                total += backfill_fx(con, args.dry_run) or 0
            if not args.dry_run:
                con.commit()
                log("COMMIT — 모든 변경사항 반영.")
        finally:
            con.close()
        _run.rows = total


if __name__ == "__main__":
    main()
