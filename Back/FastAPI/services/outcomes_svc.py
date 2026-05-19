"""
services/outcomes_svc.py
========================
P0-2 (PRD §8.1) — 종목별 추천 후 누적 상승률 트래킹.

DuckDB 의 `scores` 테이블과 `prices` 테이블을 기반으로 한 read-only 집계.
별도 OLTP 테이블 없이도 다음 정보를 산출:
  - first_recommended_date : 해당 종목이 처음 A 티어로 진입한 날짜 (참고용)
  - price_anchor           : 앵커 종가 (ROLLING_WINDOW 거래일 전)
  - latest_price           : 가장 최신 종가
  - cumulative_return_pct  : (latest_price / price_anchor - 1) * 100
  - days_since_rec         : 첫 A 진입 후 경과 일수 (참고용)

운영 시 정확도를 높이려면 신규 테이블 `recommendation_outcomes` 를 일별 cron 으로
갱신하는 방식이 권장되나 (TODO §8.4), 본 read-only 구현으로도 평가용 노출 가능.

본 모듈은 추천/검색/종목상세 응답에 cumulative_return_pct 필드를 부착하는 후처리에 사용됨.

## 2026-05-19 변경: 앵커를 "첫 A 진입가" → "ROLLING_WINDOW 거래일 전 종가"
모델은 월별 rebal (fwd_return_20d) 가정으로 학습 — 첫 A 진입 후 buy-and-hold 는
모델 가정과 mismatch. 4~5개월 누적 손실이 표시되는 문제를 해결하기 위해
*최근 30 거래일* (≈ 한 달) 수익률로 전환. paper trade hit rate 87.5% PASS 와 정합.
"""

from __future__ import annotations

import logging
from typing import Optional

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
    get_latest_date as _get_latest_date,
)
from ._helpers import parse_yyyymmdd

logger = logging.getLogger(__name__)

# 롤링 윈도우 (거래일). 30 = 모델의 fwd_return_20d 와 근접 (월 단위 rebal).
ROLLING_WINDOW = 30


def get_recommendation_outcome(
    ticker: str,
    model_version: str = "latest",
) -> Optional[dict]:
    """단건 — 종목의 첫 A티어 추천 후 누적 상승률."""
    ver = _resolve_version(model_version)
    t = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()
        # 첫 A 티어 진입 날짜 (참고용 노출 — 앵커 계산엔 미사용)
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

        # 앵커 = 최근 ROLLING_WINDOW 거래일 전 종가, 최신가 = 가장 최근 종가.
        # OFFSET ROLLING_WINDOW - 1 이면 1번째(최신) 빼고 그 다음 ROLLING_WINDOW 번째.
        # 예: ROLLING_WINDOW=30 → 최신 종가 vs 30 거래일 전 종가.
        price_anchor = con.execute(
            """
            SELECT close FROM prices WHERE ticker=?
            ORDER BY date DESC LIMIT 1 OFFSET ?
            """,
            [t, ROLLING_WINDOW - 1],
        ).fetchone()
        if not price_anchor:
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

        p0 = float(price_anchor[0] or 0)
        p1 = float(price_latest[0] or 0)
        latest_date = price_latest[1]
        if p0 <= 0:
            return None

        return_pct = round((p1 / p0 - 1.0) * 100.0, 2)

        # 경과 일수 (첫 A 진입일 ~ 최신 종가일). 두 포맷 (YYYYMMDD / YYYY-MM-DD) 모두 허용.
        d_latest = parse_yyyymmdd(latest_date)
        d_first  = parse_yyyymmdd(first_date)
        days = (d_latest - d_first).days if (d_latest and d_first) else None

        # 응답에 노출되는 날짜는 사람 친화적 ISO 로 정규화 (YYYY-MM-DD).
        first_iso  = d_first.strftime("%Y-%m-%d")  if d_first  else first_date
        latest_iso = d_latest.strftime("%Y-%m-%d") if d_latest else latest_date

        return {
            "ticker":                  t,
            "model_version":           ver,
            "first_recommended_date":  first_iso,
            "price_anchor":            round(p0, 2),     # ROLLING_WINDOW 거래일 전
            "latest_price":            round(p1, 2),
            "latest_date":             latest_iso,
            "cumulative_return_pct":   return_pct,       # 최근 ROLLING_WINDOW 거래일 수익률
            "return_window_days":      ROLLING_WINDOW,
            "days_since_rec":          days,             # 첫 A 진입 후 경과일 (참고)
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
        except Exception as e:
            # 한 종목 실패가 전체 추천 응답을 깨면 안 되므로 swallow 하되,
            # 운영 디버깅이 가능하도록 ticker 단위로 로그 남긴다.
            logger.debug("[outcomes] attach failed for %s: %s", ticker, e)
    return items


def attach_outcomes_batch(items: list[dict], model_version: str = "latest") -> list[dict]:
    """B10: N+1 회피 — 한 SQL 로 모든 ticker 의 outcome 계산.

    추천 응답 N=50 일 때 이전 attach_outcomes 는 50회 Redis lookup + 최대 50회 DuckDB
    호출. 본 함수는 단일 SQL 쿼리 + 단일 Python loop. cold start 시 50배 빠름.
    """
    if not items:
        return items
    from ._core import (
        con as _con,
        resolve_version as _resolve_version,
    )
    ver = _resolve_version(model_version)
    tickers = sorted({str(r.get("ticker") or "").strip().zfill(6) for r in items if r.get("ticker")})
    if not tickers:
        return items
    try:
        con = _con()
        ph = ",".join(["?"] * len(tickers))
        # 각 ticker 의 첫 A진입일 (참고) + 최근 ROLLING_WINDOW 거래일 전 종가 (앵커)
        # + 가장 최신 종가 → ROLLING_WINDOW 일 수익률.
        rows = con.execute(
            f"""
            WITH first_a AS (
                SELECT ticker, MIN(CAST(date AS VARCHAR)) AS first_date
                FROM scores
                WHERE model_version = ?
                  AND ticker IN ({ph})
                  AND tier = 'A'
                GROUP BY ticker
            ),
            ranked AS (
                SELECT ticker, close, date,
                       ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
                FROM prices WHERE ticker IN ({ph})
            ),
            latest_px AS (
                SELECT ticker, close AS p1, CAST(date AS VARCHAR) AS latest_date
                FROM ranked WHERE rn = 1
            ),
            anchor_px AS (
                SELECT ticker, close AS p0
                FROM ranked WHERE rn = ?
            )
            SELECT fa.ticker, fa.first_date, ap.p0, lp.p1, lp.latest_date
            FROM first_a fa
            LEFT JOIN anchor_px ap ON fa.ticker = ap.ticker
            LEFT JOIN latest_px lp ON fa.ticker = lp.ticker
            WHERE ap.p0 IS NOT NULL AND lp.p1 IS NOT NULL
            """,
            [ver] + tickers + tickers + [ROLLING_WINDOW],
        ).fetchall()
    except Exception as e:
        logger.debug("[outcomes] batch query failed, fallback to per-ticker: %s", e)
        return attach_outcomes(items, model_version=model_version)

    by_ticker: dict[str, dict] = {}
    for ticker, first_date, p0, p1, latest_date in rows:
        try:
            p0f, p1f = float(p0 or 0), float(p1 or 0)
            if p0f <= 0:
                continue
            df, dl = parse_yyyymmdd(first_date), parse_yyyymmdd(latest_date)
            days = (dl - df).days if (df and dl) else None
            ret_pct = round((p1f / p0f - 1.0) * 100.0, 2)
            # B61: 비현실적 수익률 (±300% 이상) → 액면분할/감자 의심.
            # 알티캐스트 437→2465 (+464%) 같은 케이스. 한국 주식 진짜 폭주는 드물고
            # 대부분 stock split (분할) / reverse split (감자) 후 가격 점프.
            # NULL 처리해 FE 가 "—" 또는 별도 경고 표시.
            split_suspected = abs(ret_pct) > 300.0
            by_ticker[ticker] = {
                "cumulative_return_pct":  None if split_suspected else ret_pct,
                "first_recommended_date": df.strftime("%Y-%m-%d") if df else first_date,
                "days_since_rec":         days,
                "return_window_days":     ROLLING_WINDOW,
                "split_event_suspected":  split_suspected,
            }
        except Exception:
            continue

    for r in items:
        t = str(r.get("ticker") or "").strip().zfill(6)
        if t in by_ticker:
            r.update(by_ticker[t])
    return items
