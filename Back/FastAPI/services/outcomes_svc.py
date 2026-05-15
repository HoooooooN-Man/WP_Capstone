"""
services/outcomes_svc.py
========================
P0-2 (PRD §8.1) — 종목별 추천 후 누적 상승률 트래킹.

DuckDB 의 `scores` 테이블과 `prices` 테이블을 기반으로 한 read-only 집계.
별도 OLTP 테이블 없이도 다음 정보를 산출:
  - first_recommended_date : 해당 종목이 처음 A 티어로 진입한 날짜
  - price_at_first_rec     : 그 날의 종가 (prices.close)
  - latest_price           : 가장 최신 종가
  - cumulative_return_pct  : (latest_price / price_at_first_rec - 1) * 100
  - days_since_rec         : 추천 후 경과 일수

운영 시 정확도를 높이려면 신규 테이블 `recommendation_outcomes` 를 일별 cron 으로
갱신하는 방식이 권장되나 (TODO §8.4), 본 read-only 구현으로도 평가용 노출 가능.

본 모듈은 추천/검색/종목상세 응답에 cumulative_return_pct 필드를 부착하는 후처리에 사용됨.
"""

from __future__ import annotations

from typing import Optional

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
    get_latest_date as _get_latest_date,
)


def get_recommendation_outcome(
    ticker: str,
    model_version: str = "latest",
) -> Optional[dict]:
    """단건 — 종목의 첫 A티어 추천 후 누적 상승률."""
    ver = _resolve_version(model_version)
    t = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()
        # 첫 A 티어 진입 날짜 + 종가
        row = con.execute(
            """
            SELECT CAST(MIN(date) AS VARCHAR) AS first_date
            FROM scores
            WHERE model_version=? AND ticker=? AND tier='A'
            """,
            [ver, t],
        ).fetchone()
        if not row or not row[0]:
            return None
        first_date = row[0]
        first_int = int(first_date.replace("-", ""))

        price_first = con.execute(
            """
            SELECT close FROM prices WHERE ticker=? AND date <= ?
            ORDER BY date DESC LIMIT 1
            """,
            [t, first_int],
        ).fetchone()
        if not price_first:
            return None

        price_latest = con.execute(
            """
            SELECT close, CAST(date AS VARCHAR)
            FROM prices WHERE ticker=?
            ORDER BY date DESC LIMIT 1
            """,
            [t],
        ).fetchone()
        if not price_latest:
            return None

        p0 = float(price_first[0] or 0)
        p1 = float(price_latest[0] or 0)
        latest_date = price_latest[1]
        if p0 <= 0:
            return None

        return_pct = round((p1 / p0 - 1.0) * 100.0, 2)

        # 경과 일수
        try:
            from datetime import datetime as _dt
            days = (_dt.strptime(latest_date, "%Y-%m-%d")
                    - _dt.strptime(first_date, "%Y-%m-%d")).days
        except Exception:
            days = None

        return {
            "ticker":                  t,
            "model_version":           ver,
            "first_recommended_date":  first_date,
            "price_at_first_rec":      round(p0, 2),
            "latest_price":            round(p1, 2),
            "latest_date":             latest_date,
            "cumulative_return_pct":   return_pct,
            "days_since_rec":          days,
        }

    return _cached("outcome_single", fetch, ttl=600, ticker=t, model_version=ver)


def attach_outcomes(items: list[dict], model_version: str = "latest") -> list[dict]:
    """추천/검색 결과 리스트의 각 항목에 cumulative_return_pct 필드 부착.

    티커별로 한 번씩만 outcome 을 조회 (in-loop 캐시는 Redis 가 처리).
    실패 시 필드 없이 통과 (graceful).
    """
    for r in items:
        ticker = r.get("ticker")
        if not ticker:
            continue
        try:
            outcome = get_recommendation_outcome(ticker, model_version=model_version)
            if outcome:
                r["cumulative_return_pct"]  = outcome["cumulative_return_pct"]
                r["first_recommended_date"] = outcome["first_recommended_date"]
                r["days_since_rec"]         = outcome["days_since_rec"]
        except Exception:
            pass
    return items
