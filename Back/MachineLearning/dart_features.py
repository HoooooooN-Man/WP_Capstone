"""
dart_features.py
================
차차기 W5C — DART `disclosures` 테이블 → ticker × date features.

설계 원칙:
  - *유형 코드 위주* (pblntf_detail_ty). 텍스트 파싱 X. 차차기 §절대 5 준수.
  - features = ticker × date 별 *binary* (lookback window 안 발생) + *count* (건수).
  - lookback window 기본 30일 (multi_labels y_abs_20d 와 결 비슷, 약간 길게).
  - 누수 방지: ticker 의 date d 기준 features 는 (d - window, d] 범위 공시만 사용.

핵심 detail_ty 매핑 (사용자 명세 — 자기주식·유증·실적):
  E001 자기주식취득결정    } → buyback
  E002 자기주식처분결정    }
  C001 증권신고서          → capital_increase
  A001 사업보고서          } → earnings_report
  A002 반기보고서          }
  A003 분기보고서          }

binary feature: 지난 N일 안에 *해당 카테고리* 공시가 1건이라도 있으면 1.
count feature : 지난 N일 안에 *해당 카테고리* 공시 건수.

본 모듈은 *순수 함수* — 단위 테스트 가능. DuckDB 어댑터만 외부 의존.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd


# ── 카테고리 매핑 ──────────────────────────────────────────────────────────

CATEGORY_TO_DETAIL_TY: dict[str, tuple[str, ...]] = {
    "buyback":           ("E001", "E002"),
    "capital_increase":  ("C001",),
    "earnings_report":   ("A001", "A002", "A003"),
}

DEFAULT_LOOKBACK_DAYS = 30


# ── 핵심: ticker × date features 생성 ───────────────────────────────────────

def build_features_for_ticker(
    ticker_disclosures: pd.DataFrame,
    target_dates:       pd.Series,
    *,
    categories: dict[str, tuple[str, ...]] = CATEGORY_TO_DETAIL_TY,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> pd.DataFrame:
    """
    한 ticker 의 disclosures (rcept_dt, pblntf_detail_ty) + target_dates → features DataFrame.

    target_dates: 각 d 에 대해 (d - lookback_days, d] 범위의 카테고리별 카운트·바이너리.
    *현재 d* 의 공시는 *발생 후 알려진 정보* 가 아닐 수 있어 *d 미만* 으로 보수적 처리는 caller 책임.
    본 함수는 *<=d* 포함 — 호출자가 누수 정책 선택.
    """
    if ticker_disclosures.empty:
        out = {"date": pd.to_datetime(target_dates)}
        for cat in categories:
            out[f"dart_{cat}_{lookback_days}d_count"]  = 0
            out[f"dart_{cat}_{lookback_days}d_binary"] = 0
        return pd.DataFrame(out)

    df = ticker_disclosures.copy()
    df["_dt"] = pd.to_datetime(df["rcept_dt"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["_dt"])
    df["_detail"] = df["pblntf_detail_ty"].astype(str)

    target_ts = pd.to_datetime(target_dates)
    rows: list[dict] = []
    for d in target_ts:
        window_start = d - pd.Timedelta(days=lookback_days)
        in_window = df[(df["_dt"] > window_start) & (df["_dt"] <= d)]
        rec: dict = {"date": d}
        for cat, codes in categories.items():
            mask = in_window["_detail"].isin(codes)
            cnt  = int(mask.sum())
            rec[f"dart_{cat}_{lookback_days}d_count"]  = cnt
            rec[f"dart_{cat}_{lookback_days}d_binary"] = 1 if cnt > 0 else 0
        rows.append(rec)
    return pd.DataFrame(rows)


def build_features_table(
    disclosures:   pd.DataFrame,           # 컬럼: stock_code, rcept_dt, pblntf_detail_ty
    target:        pd.DataFrame,           # 컬럼: ticker, date
    *,
    categories: dict[str, tuple[str, ...]] = CATEGORY_TO_DETAIL_TY,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> pd.DataFrame:
    """
    전체 ticker 에 대해 features 일괄. 반환: ticker, date + 각 카테고리 count/binary.
    """
    if target.empty:
        cols = ["ticker", "date"] + [
            f"dart_{cat}_{lookback_days}d_{kind}"
            for cat in categories for kind in ("count", "binary")
        ]
        return pd.DataFrame(columns=cols)

    target = target.copy()
    target["date"] = pd.to_datetime(target["date"])
    out_frames: list[pd.DataFrame] = []
    by_ticker = disclosures.groupby("stock_code") if not disclosures.empty else {}
    by_ticker_dict = {t: g for t, g in by_ticker} if not disclosures.empty else {}

    for ticker, sub_target in target.groupby("ticker"):
        sub_disc = by_ticker_dict.get(ticker, pd.DataFrame(
            columns=["stock_code", "rcept_dt", "pblntf_detail_ty"]
        ))
        feats = build_features_for_ticker(
            sub_disc, sub_target["date"],
            categories=categories, lookback_days=lookback_days,
        )
        feats.insert(0, "ticker", ticker)
        out_frames.append(feats)
    return pd.concat(out_frames, ignore_index=True) if out_frames else pd.DataFrame(
        columns=["ticker", "date"]
    )


# ── DuckDB 어댑터 ──────────────────────────────────────────────────────────

def load_disclosures_from_duckdb(
    duckdb_path: str | Path,
    *,
    detail_codes: Iterable[str] = tuple(c for codes in CATEGORY_TO_DETAIL_TY.values() for c in codes),
    bgn_de: Optional[str] = None,
    end_de: Optional[str] = None,
) -> pd.DataFrame:
    """disclosures 테이블에서 (stock_code, rcept_dt, pblntf_detail_ty) 추출.
    detail_codes 필터 + 옵션 기간. KRX 상장 종목만 (stock_code 6자리).
    """
    import duckdb
    codes_list = ",".join(f"'{c}'" for c in detail_codes)
    where = [
        f"pblntf_detail_ty IN ({codes_list})",
        "stock_code IS NOT NULL",
        "LENGTH(stock_code) = 6",
    ]
    if bgn_de:
        where.append(f"rcept_dt >= '{bgn_de}'")
    if end_de:
        where.append(f"rcept_dt <= '{end_de}'")
    sql = f"""
        SELECT stock_code, rcept_dt, pblntf_detail_ty
        FROM disclosures
        WHERE {' AND '.join(where)}
    """
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        return con.execute(sql).fetchdf()
    finally:
        con.close()


def feature_column_names(
    *,
    categories: dict[str, tuple[str, ...]] = CATEGORY_TO_DETAIL_TY,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> list[str]:
    """schema 검증용 — features build 시 생성될 컬럼 이름 list."""
    return [
        f"dart_{cat}_{lookback_days}d_{kind}"
        for cat in categories
        for kind in ("count", "binary")
    ]
