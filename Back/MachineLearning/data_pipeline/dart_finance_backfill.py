"""
dart_finance_backfill.py
========================
DART OpenAPI 로 finance 테이블 분기 backfill (C#10 후속).

운영 노트 — DART 분기보고서 dataset 반영 시차:
  분기보고서 마감일(5/15·8/14·11/14·3/31) 직후 DART 의 fnlttSinglAcnt 데이터셋
  반영까지 3~7일 시차 있음. 본문(/document.xml)은 즉시 게시되지만, finance
  데이터셋 적재는 DART 가 일괄 처리하기 때문. 분기 마감 후 매일 cron 으로
  점진 backfill 권장 (스크립트는 idempotent — 이미 채워진 ticker 자동 skip).

설계 결정:
  - DART `fnlttSinglAcnt` 는 income statement 를 **단일 분기** 값으로 반환.
    annual(11011) 만 연간 합계. (audit 가정 "cumulative" 는 오해였음.)
  - 분기-reprt_code 매핑:
        11013 = 1분기 단일
        11012 = 2분기 단일 (반기보고서가 Q2 단일을 반환)
        11014 = 3분기 단일
        11011 = 사업보고서 (annual)
  - DB finance 테이블의 Q1~Q3 행 = 단일 분기, Q4 행 = annual (기존 ETL 패턴 유지).
  - corp_code 매핑은 `disclosures` 테이블에서 추출 (3,010 ticker 커버).
  - Rate limit: 0.2s/req (5 req/s) — 일 40K 한도 안전.

사용:
  # 2025-Q3 누락 ticker 전부 backfill (실제 fetch + DB update)
  py dart_finance_backfill.py --year 2025 --quarter 3
  # 2025-Q4 누락 ticker 처음 50개만 (소규모 검증)
  py dart_finance_backfill.py --year 2025 --quarter 4 --limit 50
  # dry-run (DB 미수정)
  py dart_finance_backfill.py --year 2025 --quarter 3 --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

import duckdb
import requests

# .env 로드
BACK_DIR = Path(__file__).resolve().parents[2]
try:
    from dotenv import load_dotenv
    load_dotenv(BACK_DIR / "FastAPI" / ".env")
except ImportError:
    pass

# cron 텔레메트리 — 실행 시점·기간·결과를 cron_runs 테이블에 박제.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from cron_telemetry import track_run as _track_run
except ImportError:
    @contextlib.contextmanager  # type: ignore[no-redef]
    def _track_run(_step: str):
        class _H: rows = None
        yield _H()
import contextlib  # noqa: E402  (위 fallback 에서 필요)

DART_API_KEY = os.getenv("DART_API_KEY")
if not DART_API_KEY:
    print("FATAL: DART_API_KEY 환경변수 미설정. Back/FastAPI/.env 확인.", file=sys.stderr)
    sys.exit(2)

DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH", str(Path(r"E:\Capstone Data\project_data\db\market_data.duckdb"))))
DART_BASE   = "https://opendart.fss.or.kr/api"
RATE_SLEEP  = 0.2  # 5 req/s

# 분기 → reprt_code (DART 보고서 코드)
REPRT_CODE = {1: "11013", 2: "11012", 3: "11014", 4: "11011"}

# DART account_nm → finance 컬럼 매핑
# CFS (연결재무제표) 우선, OFS (별도) 폴백.
ACCOUNT_MAP = {
    "매출액":            "revenue",
    "수익(매출액)":      "revenue",
    "영업수익":          "revenue",
    "영업이익":          "op_profit",
    "영업이익(손실)":    "op_profit",
    "당기순이익":        "net_profit",
    "당기순이익(손실)":  "net_profit",
    "자본총계":          "equity",
    "부채총계":          "total_debt",
    "유동자산":          "current_assets",
    "유동부채":          "current_liab",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _to_float(amount: Optional[str]) -> Optional[float]:
    """DART amount 문자열 (',' 구분) → float. 빈 값/실패 → None."""
    if amount is None:
        return None
    s = str(amount).strip().replace(",", "")
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fetch_single_company(corp_code: str, year: int, quarter: int) -> Optional[dict]:
    """단일 corp 의 (year, quarter) 주요계정 dict 반환. None = 데이터 없음/실패."""
    reprt = REPRT_CODE.get(quarter)
    if not reprt:
        return None
    url = f"{DART_BASE}/fnlttSinglAcnt.json"
    params = {
        "crtfc_key":  DART_API_KEY,
        "corp_code":  corp_code,
        "bsns_year":  str(year),
        "reprt_code": reprt,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        payload = r.json()
    except Exception:
        return None
    status = payload.get("status")
    if status == "020":
        # rate limit hit — caller 가 backoff 결정
        raise RuntimeError("DART rate limit (020)")
    if status != "000":
        return None  # 데이터 없음(013) 포함 — 정상 처리

    # CFS (연결) 우선, OFS (별도) 폴백.
    items = payload.get("list", []) or []
    by_div: dict[str, dict[str, float]] = {"CFS": {}, "OFS": {}}
    for it in items:
        div = it.get("fs_div", "")
        col = ACCOUNT_MAP.get(it.get("account_nm", ""))
        if not col or div not in by_div:
            continue
        v = _to_float(it.get("thstrm_amount"))
        if v is not None and col not in by_div[div]:
            by_div[div][col] = v
    primary = by_div["CFS"] or by_div["OFS"]
    return primary or None


def derive_ratios(row: dict) -> None:
    """row 에 net_margin / op_margin / debt_ratio / current_ratio in-place."""
    rev = row.get("revenue") or 0
    if rev > 0:
        if row.get("op_profit")  is not None:
            row["op_margin"]  = round(row["op_profit"]  / rev * 100, 4)
        if row.get("net_profit") is not None:
            row["net_margin"] = round(row["net_profit"] / rev * 100, 4)
    eq = row.get("equity") or 0
    if eq > 0 and row.get("total_debt") is not None:
        row["debt_ratio"] = round(row["total_debt"] / eq * 100, 4)
    cl = row.get("current_liab") or 0
    if cl > 0 and row.get("current_assets") is not None:
        row["current_ratio"] = round(row["current_assets"] / cl * 100, 4)


def build_corp_map(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    """disclosures 에서 stock_code → corp_code 매핑."""
    rows = con.execute("""
        SELECT DISTINCT stock_code, corp_code FROM disclosures
        WHERE stock_code IS NOT NULL AND stock_code != ''
    """).fetchall()
    return {sc: cc for sc, cc in rows}


def list_targets(con: duckdb.DuckDBPyConnection, year: int, quarter: int, limit: int) -> list[str]:
    """해당 (year, quarter) 에서 revenue 가 비어 있거나 row 자체가 없는 ticker.

    finance 에 row 가 존재하나 revenue NULL 인 케이스 + stocks 에 ticker 가 있지만
    해당 분기 row 자체가 부재한 케이스 모두 포함.
    """
    rows = con.execute(f"""
        WITH existing AS (
            SELECT ticker FROM finance WHERE year = {year} AND quarter = {quarter}
                                         AND revenue IS NOT NULL
        ),
        universe AS (
            SELECT DISTINCT ticker FROM stocks
            UNION
            SELECT DISTINCT ticker FROM finance WHERE ticker IS NOT NULL
        )
        SELECT u.ticker
          FROM universe u
         WHERE u.ticker NOT IN (SELECT ticker FROM existing)
         ORDER BY u.ticker
         LIMIT {int(limit)}
    """).fetchall()
    return [r[0] for r in rows]


def upsert_row(con: duckdb.DuckDBPyConnection, ticker: str, year: int, quarter: int, data: dict, dry: bool) -> bool:
    """finance 테이블 부분 UPDATE — 기존 row 가 있으면 fields 만 set, 없으면 INSERT."""
    if dry:
        return True
    # 기존 row 존재 여부
    exists = con.execute(
        "SELECT 1 FROM finance WHERE ticker=? AND year=? AND quarter=?",
        [ticker, year, quarter],
    ).fetchone()
    fields = ["revenue", "op_profit", "net_profit", "equity", "total_debt",
              "current_assets", "current_liab", "op_margin", "net_margin",
              "debt_ratio", "current_ratio"]
    if exists:
        # SET 절 동적 — None 인 필드는 덮어쓰지 않음 (기존 값 보존)
        sets, params = [], []
        for f in fields:
            if f in data and data[f] is not None:
                sets.append(f"{f} = ?")
                params.append(data[f])
        if not sets:
            return False
        params.extend([ticker, year, quarter])
        con.execute(
            f"UPDATE finance SET {', '.join(sets)} WHERE ticker=? AND year=? AND quarter=?",
            params,
        )
    else:
        cols  = ["ticker", "year", "quarter"]
        vals  = [ticker, year, quarter]
        for f in fields:
            if f in data and data[f] is not None:
                cols.append(f)
                vals.append(data[f])
        placeholders = ",".join(["?"] * len(cols))
        con.execute(
            f"INSERT INTO finance ({','.join(cols)}) VALUES ({placeholders})",
            vals,
        )
    return True


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--year",    type=int, required=True)
    p.add_argument("--quarter", type=int, required=True, choices=[1, 2, 3, 4])
    p.add_argument("--limit",   type=int, default=10_000)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    log(f"DuckDB: {DUCKDB_PATH}")
    log(f"target: {args.year}-Q{args.quarter}  limit={args.limit}  mode={'DRY' if args.dry_run else 'WRITE'}")

    step_name = f"dart_finance_backfill_{args.year}q{args.quarter}"
    if args.dry_run:
        step_name += "_dry"

    # cron 텔레메트리로 wrap — 시작/종료/실패/rows_affected 자동 기록.
    with _track_run(step_name) as _run:
        con = duckdb.connect(str(DUCKDB_PATH), read_only=args.dry_run)
        corp_map = build_corp_map(con)
        log(f"corp_code 매핑: {len(corp_map):,} ticker")

        targets = list_targets(con, args.year, args.quarter, args.limit)
        log(f"backfill 대상: {len(targets):,} ticker")
        if not targets:
            log("대상 없음 — 종료")
            con.close()
            _run.rows = 0
            return

        ok = miss = fail = 0
        t0 = time.time()
        for i, ticker in enumerate(targets):
            if i and i % 100 == 0:
                log(f"  진행: {i:,}/{len(targets):,}  OK={ok}  miss={miss}  fail={fail}  ({(time.time()-t0)/i:.2f}s/req)")
            corp = corp_map.get(ticker)
            if not corp:
                miss += 1
                continue
            try:
                data = fetch_single_company(corp, args.year, args.quarter)
            except RuntimeError:  # rate limit
                log("  rate limit hit — 60s sleep")
                time.sleep(60)
                data = fetch_single_company(corp, args.year, args.quarter)
            except Exception as e:
                fail += 1
                log(f"  ✗ {ticker}: {e}")
                time.sleep(RATE_SLEEP)
                continue
            if not data:
                miss += 1
                time.sleep(RATE_SLEEP)
                continue
            derive_ratios(data)
            if upsert_row(con, ticker, args.year, args.quarter, data, args.dry_run):
                ok += 1
            time.sleep(RATE_SLEEP)

        if not args.dry_run:
            con.commit()
        con.close()
        log(f"DONE: OK={ok:,}  no-data={miss:,}  fail={fail:,}  elapsed={(time.time()-t0):.1f}s")
        _run.rows = ok


if __name__ == "__main__":
    main()
