"""
precompute_finance.py
=====================
financial_indicators_clean.csv → DuckDB finance 테이블 + 재무 스코어

재무 스코어 산정 기준 (100점 만점):
  - ROE         : 높을수록 좋음 (25점)
  - 부채비율     : 낮을수록 좋음 (20점)
  - 영업이익률   : 높을수록 좋음 (20점)
  - 매출액증가율 : 높을수록 좋음 YoY (15점)
  - PBR         : 낮을수록 좋음 (10점)
  - 유동비율     : 높을수록 좋음 (10점)
  각 항목은 분기 내 백분위 기반 정규화 후 가중합산
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
_THIS  = Path(__file__).resolve()
_BACK  = _THIS.parent.parent
_REPO  = _BACK.parent
CAPSTONE_ROOT = _REPO.parent

FINANCE_CSV  = CAPSTONE_ROOT / "preprocessing" / "financial_indicators_clean.csv"
DUCKDB_PATH  = _BACK / "FastAPI" / "scores.duckdb"

# ── 컬럼 매핑 ─────────────────────────────────────────────────────────────────
COL_MAP = {
    "종목코드":            "ticker",
    "회사명":              "name",
    "연도":                "year",
    "분기":                "quarter",
    "기준일":              "base_date",
    "시가총액":            "market_cap",
    "PER":                 "per",
    "PBR":                 "pbr",
    "EPS":                 "eps",
    "BPS":                 "bps",
    "DPS":                 "dps",
    "배당수익률(%)":       "dividend_yield",
    "영업이익률(%)":       "op_margin",
    "순이익률(%)":         "net_margin",
    "ROE(%)":              "roe",
    "부채비율(%)":         "debt_ratio",
    "유동비율(%)":         "current_ratio",
    "매출액":              "revenue",
    "영업이익":            "op_profit",
    "당기순이익":          "net_profit",
    "자본총계":            "equity",
    "부채총계":            "total_debt",
    "유동자산":            "current_assets",
    "유동부채":            "current_liab",
    "매출액증가율(YoY,%)": "rev_growth_yoy",
    "매출액증가율(QoQ,%)": "rev_growth_qoq",
    "영업이익증가율(YoY,%)": "op_growth_yoy",
    "영업이익증가율(QoQ,%)": "op_growth_qoq",
}

# ── 스코어 가중치 (합 = 100) ──────────────────────────────────────────────────
SCORE_WEIGHTS = {
    "roe":           25.0,   # 높을수록 좋음
    "debt_ratio":    20.0,   # 낮을수록 좋음 (역순 백분위)
    "op_margin":     20.0,   # 높을수록 좋음
    "rev_growth_yoy": 15.0,  # 높을수록 좋음
    "pbr":           10.0,   # 낮을수록 좋음 (역순 백분위)
    "current_ratio": 10.0,   # 높을수록 좋음
}
LOWER_IS_BETTER = {"debt_ratio", "pbr"}


def percentile_rank(series: pd.Series, lower_is_better: bool = False) -> pd.Series:
    """0~100 백분위 순위. NaN은 50으로 채움."""
    ranks = series.rank(pct=True, ascending=not lower_is_better, na_option="keep") * 100
    return ranks.fillna(50.0)


def compute_finance_score(df: pd.DataFrame) -> pd.DataFrame:
    """분기별 상대 재무 스코어 산정."""
    print("[finance] 재무 스코어 계산 중...")
    df = df.copy()
    df["finance_score"] = 0.0

    groups = df.groupby(["year", "quarter"])
    scored_parts = []

    for (yr, qt), grp in groups:
        part = grp.copy()
        total = 0.0
        for col, weight in SCORE_WEIGHTS.items():
            if col not in part.columns:
                continue
            lb = col in LOWER_IS_BETTER
            part[f"_rank_{col}"] = percentile_rank(part[col], lower_is_better=lb)
            total += weight

        if total == 0:
            part["finance_score"] = 50.0
        else:
            score = sum(
                part[f"_rank_{col}"] * (weight / total)
                for col, weight in SCORE_WEIGHTS.items()
                if f"_rank_{col}" in part.columns
            )
            part["finance_score"] = score.clip(0, 100).round(1)

        # 임시 컬럼 제거
        drop_cols = [c for c in part.columns if c.startswith("_rank_")]
        part = part.drop(columns=drop_cols)
        scored_parts.append(part)

    result = pd.concat(scored_parts, ignore_index=True)
    print(f"[finance] 스코어 완료 — 평균: {result['finance_score'].mean():.1f}")
    return result


def load_and_clean(csv_path: Path) -> pd.DataFrame:
    print(f"[finance] CSV 로드: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype={"종목코드": str})

    missing = [k for k in COL_MAP if k not in df.columns]
    if missing:
        print(f"[finance] 경고: 없는 컬럼 {missing} — 스킵")

    rename_map = {k: v for k, v in COL_MAP.items() if k in df.columns}
    df = df[list(rename_map)].rename(columns=rename_map)

    df["ticker"] = df["ticker"].str.zfill(6)

    # 기준일: float → int → string 'YYYY-MM-DD'
    df["base_date"] = (
        pd.to_numeric(df["base_date"], errors="coerce")
          .dropna()
          .astype(int)
          .pipe(lambda s: pd.to_datetime(s.astype(str), format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d"))
    )
    # base_date가 NaN인 행도 유지 (연도+분기로 식별 가능)
    df["base_date"] = df["base_date"].where(df["base_date"].notna(), None)

    numeric_cols = [c for c in df.columns if c not in ("ticker", "name", "base_date")]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    df = df.sort_values(["ticker", "year", "quarter"]).reset_index(drop=True)
    print(f"[finance] 유효 행: {len(df):,}  티커 수: {df['ticker'].nunique():,}")
    return df


def save_to_duckdb(df: pd.DataFrame, db_path: Path, overwrite: bool) -> None:
    print(f"[finance] DuckDB 저장: {db_path}")
    con = duckdb.connect(str(db_path))

    con.execute("""
        CREATE TABLE IF NOT EXISTS finance (
            ticker          VARCHAR NOT NULL,
            name            VARCHAR,
            year            INTEGER,
            quarter         INTEGER,
            base_date       VARCHAR,
            market_cap      DOUBLE,
            per             DOUBLE,
            pbr             DOUBLE,
            eps             DOUBLE,
            bps             DOUBLE,
            dps             DOUBLE,
            dividend_yield  DOUBLE,
            op_margin       DOUBLE,
            net_margin      DOUBLE,
            roe             DOUBLE,
            debt_ratio      DOUBLE,
            current_ratio   DOUBLE,
            revenue         DOUBLE,
            op_profit       DOUBLE,
            net_profit      DOUBLE,
            equity          DOUBLE,
            total_debt      DOUBLE,
            current_assets  DOUBLE,
            current_liab    DOUBLE,
            rev_growth_yoy  DOUBLE,
            rev_growth_qoq  DOUBLE,
            op_growth_yoy   DOUBLE,
            op_growth_qoq   DOUBLE,
            finance_score   DOUBLE,
            PRIMARY KEY (ticker, year, quarter)
        )
    """)

    if overwrite:
        con.execute("DELETE FROM finance")
        print("[finance] 기존 finance 데이터 삭제 완료")

    # 스키마와 df 컬럼 맞추기
    expected = [
        "ticker","name","year","quarter","base_date","market_cap","per","pbr",
        "eps","bps","dps","dividend_yield","op_margin","net_margin","roe",
        "debt_ratio","current_ratio","revenue","op_profit","net_profit",
        "equity","total_debt","current_assets","current_liab",
        "rev_growth_yoy","rev_growth_qoq","op_growth_yoy","op_growth_qoq",
        "finance_score",
    ]
    for col in expected:
        if col not in df.columns:
            df[col] = None
    df = df[expected]

    con.execute("INSERT OR IGNORE INTO finance SELECT * FROM df")
    count = con.execute("SELECT COUNT(*) FROM finance").fetchone()[0]
    print(f"[finance] finance 테이블 총 {count:,}행")
    con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="financial_indicators_clean.csv → DuckDB finance")
    parser.add_argument("--csv",       default=str(FINANCE_CSV),  help="입력 CSV 경로")
    parser.add_argument("--db",        default=str(DUCKDB_PATH),  help="DuckDB 경로")
    parser.add_argument("--overwrite", action="store_true",       help="기존 데이터 삭제 후 재적재")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    db_path  = Path(args.db)

    if not csv_path.exists():
        print(f"[오류] CSV 없음: {csv_path}", file=sys.stderr)
        sys.exit(1)

    df = load_and_clean(csv_path)
    df = compute_finance_score(df)
    save_to_duckdb(df, db_path, overwrite=args.overwrite)
    print("[finance] 완료!")


if __name__ == "__main__":
    main()
