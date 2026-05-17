"""
dart_bulk_missing.py
====================
finance 테이블 EPS 누락 종목 대량 DART 백필.

설계:
  - 대상: finance.최신분기 eps IS NULL 인 종목 (보통 1,500+ 소형주/은행/특수회계).
  - corp_code 는 disclosures 테이블에서 조회.
  - DART fnlttSinglAcnt 분기별 fetch (CFS 우선, fail시 OFS).
  - 은행/보험 회계 확장 ACCOUNT_MAP (이자수익, 영업수익, 보험료수익).
  - shares_outstanding 은 prices 테이블에서 직접.
  - EPS = net_profit / shares_outstanding, BPS = total_equity / shares_outstanding.
  - PER/PBR/ROE/debt_ratio 자동 계산 (분기 말일 종가 기준).
  - 이미 채워진 (ticker, year, quarter) 자동 skip — idempotent.

사용:
  py dart_bulk_missing.py --year 2024 --quarter 4 --limit 100
  py dart_bulk_missing.py --year 2025 --quarter 2          # 전체
  py dart_bulk_missing.py --year 2025 --quarter 2 --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb
import requests
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BACK_DIR = Path(__file__).resolve().parents[2]
try:
    from dotenv import load_dotenv
    load_dotenv(BACK_DIR / "FastAPI" / ".env")
except ImportError:
    pass

DART_API_KEY = os.getenv("DART_API_KEY")
if not DART_API_KEY:
    print("FATAL: DART_API_KEY 미설정", file=sys.stderr)
    sys.exit(2)

DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH",
                              r"E:\Capstone Data\project_data\db\market_data.duckdb"))
DART_BASE   = "https://opendart.fss.or.kr/api"
RATE_SLEEP  = 0.2   # 5 req/s

REPRT_CODE = {1: "11013", 2: "11012", 3: "11014", 4: "11011"}
QUARTER_END = {1: "0331", 2: "0630", 3: "0930", 4: "1231"}

# 확장 ACCOUNT_MAP — 일반 + 은행/보험/IT.
ACCOUNT_MAP = {
    # 매출
    "매출액": "revenue", "수익(매출액)": "revenue", "영업수익": "revenue",
    "이자수익": "revenue",  # 은행
    "보험료수익": "revenue",  # 보험
    "총포괄수익": "revenue",  # 일부 IFRS
    # 영업이익
    "영업이익": "op_profit", "영업이익(손실)": "op_profit", "영업손익": "op_profit",
    # 순이익
    "당기순이익": "net_profit", "당기순이익(손실)": "net_profit", "당기순손익": "net_profit",
    # 자본/부채
    "자산총계": "total_assets",
    "부채총계": "total_liab",
    "자본총계": "total_equity",
}


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch_dart(corp_code: str, year: int, quarter: int) -> dict | None:
    """CFS 우선, fail 시 OFS. account_nm → 값 dict 반환."""
    for fs_div in ("CFS", "OFS"):
        try:
            r = requests.get(
                f"{DART_BASE}/fnlttSinglAcnt.json",
                params={
                    "crtfc_key": DART_API_KEY,
                    "corp_code": corp_code,
                    "bsns_year": year,
                    "reprt_code": REPRT_CODE[quarter],
                    "fs_div":     fs_div,
                },
                timeout=15,
            )
            d = r.json()
            if d.get("status") != "000":
                continue
            out = {}
            for item in d.get("list", []):
                an = item.get("account_nm")
                col = ACCOUNT_MAP.get(an)
                if not col or col in out:
                    continue
                amt = (item.get("thstrm_amount") or "").replace(",", "").strip()
                if not amt or amt == "-":
                    continue
                try:
                    out[col] = float(amt)
                except ValueError:
                    continue
            if out:
                return out
        except Exception:
            continue
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="DART 누락 종목 대량 백필")
    parser.add_argument("--year",    type=int, required=True)
    parser.add_argument("--quarter", type=int, required=True, choices=[1, 2, 3, 4])
    parser.add_argument("--limit",   type=int, default=None, help="처음 N 종목만 처리 (테스트용)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log(f"=== dart_bulk_missing {args.year} Q{args.quarter} ===")

    con = duckdb.connect(str(DUCKDB_PATH), read_only=args.dry_run)

    # 1) 대상 종목 + corp_code + shares
    sql = """
    WITH lq AS (
        SELECT ticker, eps,
            ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY year DESC, quarter DESC) rn
        FROM finance
    ),
    nulls AS (SELECT ticker FROM lq WHERE rn=1 AND eps IS NULL),
    corps AS (
        SELECT DISTINCT stock_code, FIRST(corp_code) OVER (PARTITION BY stock_code) AS corp_code
        FROM disclosures
    ),
    lp AS (
        SELECT ticker, shares_outstanding,
            ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
        FROM prices
    ),
    have_q AS (
        SELECT ticker FROM finance
        WHERE year=? AND quarter=? AND eps IS NOT NULL
    )
    SELECT n.ticker, c.corp_code, lp.shares_outstanding
    FROM nulls n
    INNER JOIN corps c ON n.ticker=c.stock_code
    LEFT JOIN lp ON n.ticker=lp.ticker AND lp.rn=1
    LEFT JOIN have_q hq ON n.ticker=hq.ticker
    WHERE hq.ticker IS NULL
      AND c.corp_code IS NOT NULL
      AND lp.shares_outstanding > 0
    """
    targets = con.execute(sql, [args.year, args.quarter]).fetchall()
    if args.limit:
        targets = targets[:args.limit]
    log(f"  대상: {len(targets)} 종목 ({args.year}Q{args.quarter})")
    if not targets:
        log("  처리할 종목 없음."); con.close(); return 0

    # 2) 분기 말일 종가 (PER/PBR 계산용)
    base_date = int(f"{args.year}{QUARTER_END[args.quarter]}")

    rows_out = []
    ok = 0; fail = 0
    for i, (ticker, corp, shares) in enumerate(targets):
        if (i+1) % 50 == 0:
            log(f"  진행 {i+1}/{len(targets)} (ok={ok}, fail={fail})")
        data = fetch_dart(corp, args.year, args.quarter)
        time.sleep(RATE_SLEEP)
        if not data:
            fail += 1; continue
        net_p = data.get("net_profit")
        equity = data.get("total_equity")
        if net_p is None and equity is None:
            fail += 1; continue
        eps = (net_p / shares) if net_p else None
        bps = (equity / shares) if equity else None
        rows_out.append({
            "ticker": ticker, "year": args.year, "quarter": args.quarter,
            "base_date": base_date,
            "revenue": data.get("revenue"), "op_profit": data.get("op_profit"),
            "net_profit": net_p,
            "total_assets": data.get("total_assets"),
            "total_liab": data.get("total_liab"),
            "total_equity": equity,
            "eps": eps, "bps": bps,
            "roe": (net_p/equity*100.0) if (net_p and equity) else None,
            "debt_ratio": (data.get("total_liab")/equity*100.0) if (data.get("total_liab") and equity) else None,
            "op_margin": (data.get("op_profit")/data.get("revenue")*100.0) if (data.get("op_profit") and data.get("revenue")) else None,
            "net_margin": (net_p/data.get("revenue")*100.0) if (net_p and data.get("revenue")) else None,
        })
        ok += 1

    log(f"  완료: ok={ok}, fail={fail}")

    if args.dry_run:
        log("[dry-run] DB 미수정. 샘플:")
        for r in rows_out[:3]: print(" ", r)
        con.close(); return 0

    if not rows_out:
        con.close(); return 0

    # 3) per/pbr — 분기 말일 가까운 종가 조회
    df = pd.DataFrame(rows_out)
    for i, r in df.iterrows():
        cls = con.execute(
            "SELECT close FROM prices WHERE ticker=? AND date<=? ORDER BY date DESC LIMIT 1",
            [r.ticker, int(r.base_date)],
        ).fetchone()
        c = float(cls[0]) if cls and cls[0] else None
        if c:
            if r.eps and r.eps > 0: df.at[i, "per"] = c / r.eps
            if r.bps and r.bps > 0: df.at[i, "pbr"] = c / r.bps

    # 4) finance 컬럼 정렬 + INSERT
    fcols = [r[1] for r in con.execute("PRAGMA table_info('finance')").fetchall()]
    for c in fcols:
        if c not in df.columns: df[c] = None
    df_ins = df[fcols]
    con.register("fin_in", df_ins)
    con.execute("INSERT INTO finance SELECT * FROM fin_in")
    log(f"  INSERT 완료: {len(df_ins)} 행")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
