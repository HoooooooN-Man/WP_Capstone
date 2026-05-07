"""
services/finance_svc.py
=======================
Tier 1B 4.5 — `data.py` 분할 결과물.

분기별 재무 도메인.
함수: get_finance, get_finance_latest
"""

from __future__ import annotations

import pandas as pd

from ._core import (
    con as _con,
    cached as _cached,
)


def get_finance(ticker: str, limit: int = 20) -> tuple[list[dict], str | None]:
    """분기별 재무 이력 (최신순 N개).

    Redis 에 (rows, name) 튜플을 JSON 직렬화하면 역직렬화 시 list 가 되어
    클라이언트에 잘못 전달될 수 있으므로 dict 로만 캐시한다.
    """
    tkey = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()
        t = tkey
        sql = """
            SELECT
                f.year, f.quarter, f.base_date, f.market_cap,
                f.per, f.pbr, f.eps, f.bps, f.dps, f.dividend_yield,
                f.op_margin, f.net_margin, f.roe, f.debt_ratio, f.current_ratio,
                f.revenue, f.op_profit, f.net_profit,
                f.equity, f.total_debt, f.current_assets, f.current_liab,
                f.rev_growth_yoy, f.rev_growth_qoq, f.op_growth_yoy, f.op_growth_qoq,
                f.finance_score,
                COALESCE(f.name, st.name) AS name
            FROM finance f
            LEFT JOIN stocks st ON f.ticker = st.ticker
            WHERE f.ticker = ?
            ORDER BY f.year DESC, f.quarter DESC
            LIMIT ?
        """
        rows = con.execute(sql, [t, limit]).fetchdf()
        if rows.empty:
            return {"rows": [], "name": None}
        name_val = rows["name"].iloc[0] if "name" in rows.columns else None
        # base_date: float(YYYYMMDD.0) → 'YYYYMMDD' 문자열 (스키마 호환)
        if "base_date" in rows.columns:
            rows["base_date"] = rows["base_date"].apply(
                lambda v: str(int(v)) if pd.notna(v) else None
            )
        data_rows = rows.drop(columns=["name"]).to_dict(orient="records")
        return {"rows": data_rows, "name": name_val}

    result = _cached("finance_v2", fetch, ttl=600, ticker=tkey, limit=int(limit))
    if not isinstance(result, dict):
        return [], None
    return result.get("rows") or [], result.get("name")


def get_finance_latest(ticker: str) -> dict | None:
    """가장 최근 분기 재무 요약."""
    tkey = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()
        t = tkey
        sql = """
            SELECT
                f.ticker,
                COALESCE(f.name, st.name) AS name,
                f.year, f.quarter, f.base_date,
                f.per, f.pbr, f.eps, f.roe, f.debt_ratio, f.op_margin,
                f.rev_growth_yoy, f.finance_score
            FROM finance f
            LEFT JOIN stocks st ON f.ticker = st.ticker
            WHERE f.ticker = ?
            ORDER BY f.year DESC, f.quarter DESC
            LIMIT 1
        """
        row = con.execute(sql, [t]).fetchdf()
        if row.empty:
            return None
        if "base_date" in row.columns:
            row["base_date"] = row["base_date"].apply(
                lambda v: str(int(v)) if pd.notna(v) else None
            )
        return row.to_dict(orient="records")[0]

    return _cached("finance_latest", fetch, ttl=600, ticker=tkey)
