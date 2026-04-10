"""
precompute_chart.py
===================
stock_data_clean.csv → DuckDB prices 테이블

컬럼 매핑:
  종목코드 → ticker        일자   → date
  시가     → open          고가   → high
  저가     → low           종가   → close
  거래량   → volume        거래대금 → amount
  시가총액 → market_cap

이동평균: MA5, MA20, MA60, MA120
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
_THIS  = Path(__file__).resolve()
_BACK  = _THIS.parent.parent           # Back/
_REPO  = _BACK.parent                  # WP_Capstone/
CAPSTONE_ROOT = _REPO.parent           # Capstone Data/

STOCK_CSV  = CAPSTONE_ROOT / "data" / "stock_data_clean.csv"
DUCKDB_PATH = _BACK / "FastAPI" / "scores.duckdb"

# ── 컬럼 매핑 ─────────────────────────────────────────────────────────────────
COL_MAP = {
    "종목코드": "ticker",
    "일자":     "date",
    "시가":     "open",
    "고가":     "high",
    "저가":     "low",
    "종가":     "close",
    "거래량":   "volume",
    "거래대금": "amount",
    "시가총액": "market_cap",
}


def load_and_clean(csv_path: Path) -> pd.DataFrame:
    print(f"[chart] CSV 로드: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype={"종목코드": str})

    missing = [k for k in COL_MAP if k not in df.columns]
    if missing:
        raise ValueError(f"CSV에 없는 컬럼: {missing}")

    df = df[list(COL_MAP)].rename(columns=COL_MAP)

    # ticker zero-padding (6자리)
    df["ticker"] = df["ticker"].str.zfill(6)

    # 날짜 정수 → 'YYYY-MM-DD'
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d").dt.strftime("%Y-%m-%d")

    numeric_cols = ["open", "high", "low", "close", "volume", "amount", "market_cap"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    df = df.dropna(subset=["close"]).sort_values(["ticker", "date"]).reset_index(drop=True)
    print(f"[chart] 유효 행: {len(df):,}  티커 수: {df['ticker'].nunique():,}")
    return df


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    print("[chart] 이동평균 계산 중...")
    for win in [5, 20, 60, 120]:
        df[f"ma{win}"] = (
            df.groupby("ticker")["close"]
              .transform(lambda s: s.rolling(win, min_periods=1).mean().round(2))
        )
    return df


def save_to_duckdb(df: pd.DataFrame, db_path: Path, overwrite: bool) -> None:
    print(f"[chart] DuckDB 저장: {db_path}")
    con = duckdb.connect(str(db_path))

    con.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ticker      VARCHAR NOT NULL,
            date        VARCHAR NOT NULL,
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE,
            volume      DOUBLE,
            amount      DOUBLE,
            market_cap  DOUBLE,
            ma5         DOUBLE,
            ma20        DOUBLE,
            ma60        DOUBLE,
            ma120       DOUBLE,
            PRIMARY KEY (ticker, date)
        )
    """)

    if overwrite:
        con.execute("DELETE FROM prices")
        print("[chart] 기존 prices 데이터 삭제 완료")

    con.execute("INSERT OR IGNORE INTO prices SELECT * FROM df")
    count = con.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    print(f"[chart] prices 테이블 총 {count:,}행")
    con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="stock_data_clean.csv → DuckDB prices")
    parser.add_argument("--csv",      default=str(STOCK_CSV),  help="입력 CSV 경로")
    parser.add_argument("--db",       default=str(DUCKDB_PATH), help="DuckDB 경로")
    parser.add_argument("--overwrite", action="store_true",    help="기존 데이터 삭제 후 재적재")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    db_path  = Path(args.db)

    if not csv_path.exists():
        print(f"[오류] CSV 없음: {csv_path}", file=sys.stderr)
        sys.exit(1)

    df = load_and_clean(csv_path)
    df = add_moving_averages(df)
    save_to_duckdb(df, db_path, overwrite=args.overwrite)
    print("[chart] 완료!")


if __name__ == "__main__":
    main()
