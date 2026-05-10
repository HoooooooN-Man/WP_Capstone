"""
dart_ingest.py
==============
차차기 W5 — DART 공시 → DuckDB `disclosures` 테이블 적재.

흐름:
  1. dart_client.iter_disclosures (기간 + 유형 옵션) → row 스트림.
  2. KRX 상장 종목만 필터 (stock_code 비어있지 않은 것 — 비상장 corp 제외).
  3. DuckDB UPSERT (PK=rcept_no, idempotent 재실행).

설계:
  - *공시 유형 코드 위주* (pblntf_ty, pblntf_detail_ty). 텍스트 파싱 없음.
  - DuckDB 단일 writer + multi reader 정책 유지 (W4 multi_labels 패턴 동일).
  - 일별 쪼개 호출 권장 (큰 기간은 페이지·rate limit 부하 큼).

사용:
  py dart_ingest.py --start 2026-01-01 --end 2026-01-31      # 한 달
  py dart_ingest.py --start 2026-01-02 --end 2026-01-02      # 하루
  py dart_ingest.py --start 2026-01-02 --end 2026-01-02 --pblntf-ty B  # 주요사항만
  py dart_ingest.py --start ... --end ... --dry-run          # 적재 생략
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dart_client import DartConfig, DartError, iter_disclosures


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data"))
DUCKDB_PATH   = Path(os.getenv("DUCKDB_PATH",
                               str(CAPSTONE_ROOT / "project_data" / "db" / "market_data.duckdb")))


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 스키마 ──────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS disclosures (
    rcept_no          VARCHAR PRIMARY KEY,
    corp_code         VARCHAR,
    corp_name         VARCHAR,
    stock_code        VARCHAR,        -- KRX 6자리, 비상장은 NULL/공백
    corp_cls          VARCHAR,        -- Y(KOSPI)/K(KOSDAQ)/N(KONEX)/E(기타)
    rcept_dt          VARCHAR,        -- YYYYMMDD
    report_nm         VARCHAR,
    pblntf_ty         VARCHAR,        -- A~J (caller 호출 시 명시 한정 시만 채워짐)
    pblntf_detail_ty  VARCHAR,
    flr_nm            VARCHAR,
    rm                VARCHAR,
    inserted_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# 기존 테이블에 corp_cls 컬럼이 없으면 ALTER 추가 (이전 적재 호환).
ALTER_ADD_CORP_CLS_SQL = """
ALTER TABLE disclosures ADD COLUMN IF NOT EXISTS corp_cls VARCHAR
"""


def ensure_table(con) -> None:
    con.execute(CREATE_TABLE_SQL)
    try:
        con.execute(ALTER_ADD_CORP_CLS_SQL)
    except Exception:
        pass    # ADD COLUMN IF NOT EXISTS 미지원 DuckDB 구버전 — graceful skip


# ── 행 정규화 ──────────────────────────────────────────────────────────────

def normalize_row(row: dict) -> Optional[dict]:
    """API 응답 row → DuckDB 행. 필수 필드 누락 시 None."""
    rcept_no = (row.get("rcept_no") or "").strip()
    if not rcept_no:
        return None
    return {
        "rcept_no":          rcept_no,
        "corp_code":         (row.get("corp_code") or "").strip() or None,
        "corp_name":         (row.get("corp_name") or "").strip() or None,
        "stock_code":        (row.get("stock_code") or "").strip() or None,
        "corp_cls":          (row.get("corp_cls") or "").strip() or None,
        "rcept_dt":          (row.get("rcept_dt") or "").strip() or None,
        "report_nm":         (row.get("report_nm") or "").strip() or None,
        "pblntf_ty":         (row.get("pblntf_ty") or "").strip() or None,
        "pblntf_detail_ty":  (row.get("pblntf_detail_ty") or "").strip() or None,
        "flr_nm":            (row.get("flr_nm") or "").strip() or None,
        "rm":                (row.get("rm") or "").strip() or None,
    }


def filter_listed(rows: Iterable[dict]) -> Iterator[dict]:
    """stock_code 가 6자리 KRX 코드인 행만 (상장 종목)."""
    for r in rows:
        sc = r.get("stock_code")
        if sc and len(sc) == 6 and sc.isdigit():
            yield r


# ── UPSERT ──────────────────────────────────────────────────────────────────

UPSERT_SQL = """
INSERT INTO disclosures (
    rcept_no, corp_code, corp_name, stock_code, corp_cls, rcept_dt,
    report_nm, pblntf_ty, pblntf_detail_ty, flr_nm, rm
)
SELECT rcept_no, corp_code, corp_name, stock_code, corp_cls, rcept_dt,
       report_nm, pblntf_ty, pblntf_detail_ty, flr_nm, rm
FROM upsert_df
ON CONFLICT (rcept_no) DO UPDATE SET
    corp_code        = EXCLUDED.corp_code,
    corp_name        = EXCLUDED.corp_name,
    stock_code       = EXCLUDED.stock_code,
    corp_cls         = EXCLUDED.corp_cls,
    rcept_dt         = EXCLUDED.rcept_dt,
    report_nm        = EXCLUDED.report_nm,
    pblntf_ty        = EXCLUDED.pblntf_ty,
    pblntf_detail_ty = EXCLUDED.pblntf_detail_ty,
    flr_nm           = EXCLUDED.flr_nm,
    rm               = EXCLUDED.rm,
    inserted_at      = NOW()
"""


def upsert_rows(con, rows: list[dict]) -> int:
    """DataFrame register + INSERT FROM SELECT (벡터화). 0행이면 no-op."""
    if not rows:
        return 0
    import pandas as pd
    df = pd.DataFrame(rows)
    con.register("upsert_df", df)
    con.execute(UPSERT_SQL)
    con.unregister("upsert_df")
    return len(rows)


# ── 일별 쪼개 호출 ─────────────────────────────────────────────────────────

def _daterange(start: date, end: date) -> Iterator[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


# ── 메인 ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="W5 — DART 공시 → DuckDB 적재")
    parser.add_argument("--start",     required=True, help="YYYY-MM-DD")
    parser.add_argument("--end",       required=True)
    parser.add_argument("--pblntf-ty", default=None,  help="공시유형 1차 (A~J). 미명시면 전체.")
    parser.add_argument("--pblntf-detail-ty", default=None,
                        help="공시유형 2차 (예: A001 사업보고서, E001 자기주식취득결정).")
    parser.add_argument("--listed-only", action="store_true",
                        help="KRX 상장 종목만 (stock_code 6자리). default: 전체.")
    parser.add_argument("--dry-run",   action="store_true")
    args = parser.parse_args()

    start_d = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_d   = datetime.strptime(args.end,   "%Y-%m-%d").date()
    if start_d > end_d:
        log(f"[ERROR] start > end: {start_d} > {end_d}")
        return 1

    log("=== dart_ingest (W5 Step 1) ===")
    log(f"  range:    {start_d} ~ {end_d}")
    log(f"  pblntf_ty: {args.pblntf_ty or '<all>'}")
    log(f"  filter:    {'listed only' if args.listed_only else 'all'}")
    log(f"  DuckDB:    {DUCKDB_PATH}")

    try:
        config = DartConfig.from_env()
    except DartError as e:
        log(f"[ERROR] {e}")
        return 2

    import duckdb
    con = duckdb.connect(str(DUCKDB_PATH)) if not args.dry_run else None
    if con is not None:
        ensure_table(con)

    total_seen   = 0
    total_kept   = 0
    total_upsert = 0
    try:
        for d in _daterange(start_d, end_d):
            ymd = _yyyymmdd(d)
            day_rows: list[dict] = []
            try:
                stream = iter_disclosures(
                    config=config, bgn_de=ymd, end_de=ymd,
                    pblntf_ty=args.pblntf_ty,
                    pblntf_detail_ty=args.pblntf_detail_ty,
                )
                for row in stream:
                    total_seen += 1
                    nrow = normalize_row(row)
                    if nrow is None:
                        continue
                    if args.listed_only:
                        sc = nrow.get("stock_code")
                        if not (sc and len(sc) == 6 and sc.isdigit()):
                            continue
                    day_rows.append(nrow)
            except DartError as e:
                log(f"[WARN] {ymd}: {e}")
                continue

            total_kept += len(day_rows)
            if con is not None and day_rows:
                total_upsert += upsert_rows(con, day_rows)
            log(f"  {ymd}: seen=...  kept={len(day_rows):>5}  cumul_kept={total_kept:,}")
    finally:
        if con is not None:
            con.close()

    log(f"  Done. total seen: {total_seen:,}  kept: {total_kept:,}  "
        f"{'would-be ' if args.dry_run else ''}upserted: {total_upsert:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
