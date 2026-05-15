"""
services/winners_svc.py
=======================
PRD §3.4 — 일자별 승부주 (Top-5) 이력.

`scores` 테이블에 80여 거래일치 일자별 점수가 적재돼 있으므로 별도 스냅샷
테이블 없이 직접 도출한다. scores 에 중복 행이 존재하고 `rank_in_date` 가
신뢰 불가하므로 DISTINCT + score DESC 재랭킹한다.

각 승부주에 대해:
  - recommend_price : 추천일 종가 (scores.close)
  - cumulative_return_pct : (현재가 - 추천가) / 추천가 * 100
  - trend : 추천일 이후 +5 / +20 / +60 거래일 수익률 → up/neutral/down 마커
"""

from __future__ import annotations

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
)

_TREND_UP = 3.0     # +3% 초과 → up
_TREND_DOWN = -3.0  # -3% 미만 → down


def _marker(pct: float | None) -> str:
    if pct is None:
        return "neutral"
    if pct > _TREND_UP:
        return "up"
    if pct < _TREND_DOWN:
        return "down"
    return "neutral"


def get_winners(days_back: int = 21, top_k: int = 5, model_version: str = "latest") -> dict:
    """최근 `days_back` 거래일의 일자별 Top-`top_k` 승부주.

    반환: {"model_version", "items": [{"date", "winners": [...]}, ...]}  (날짜 DESC)
    """
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()

        # 1) dedup + 재랭킹 + 최근 N거래일 + 현재가 조인
        rows = con.execute(
            """
            WITH dates AS (
                SELECT DISTINCT CAST(date AS VARCHAR) AS d
                FROM scores WHERE model_version = ?
                ORDER BY d DESC LIMIT ?
            ),
            dedup AS (
                SELECT DISTINCT
                    CAST(s.date AS VARCHAR)        AS d,
                    s.ticker,
                    COALESCE(s.name, st.name)      AS nm,
                    COALESCE(s.sector, st.wics_large_name) AS sector,
                    ROUND(CAST(s.score AS DOUBLE), 1) AS score,
                    s.tier,
                    s.close
                FROM scores s
                LEFT JOIN stocks st ON s.ticker = st.ticker
                WHERE s.model_version = ?
                  AND CAST(s.date AS VARCHAR) IN (SELECT d FROM dates)
            ),
            ranked AS (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY d ORDER BY score DESC, ticker
                ) AS rnk
                FROM dedup
            ),
            win AS (SELECT * FROM ranked WHERE rnk <= ?),
            latest_px AS (
                SELECT ticker, close FROM (
                    SELECT ticker, close,
                           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
                    FROM prices
                ) WHERE rn = 1
            )
            SELECT
                w.d, w.rnk, w.ticker, w.nm, w.sector, w.score, w.tier, w.close,
                lp.close AS cur_close,
                ROUND((lp.close - w.close) / NULLIF(w.close, 0) * 100, 2) AS cum_ret
            FROM win w
            LEFT JOIN latest_px lp ON w.ticker = lp.ticker
            ORDER BY w.d DESC, w.rnk
            """,
            [ver, days_back, ver, top_k],
        ).fetchall()

        if not rows:
            return {"model_version": ver, "items": []}

        # 2) trend 계산용 — 관련 ticker 들의 추천일 이후 가격 시계열 일괄 조회
        tickers = sorted({r[2] for r in rows})
        min_date_int = min(int(r[0].replace("-", "")) for r in rows)
        ph = ",".join(["?"] * len(tickers))
        px_rows = con.execute(
            f"""
            SELECT ticker, date, close
            FROM prices
            WHERE ticker IN ({ph}) AND date >= ?
            ORDER BY ticker, date
            """,
            tickers + [min_date_int],
        ).fetchall()

        # ticker → [(date_int, close), ...] (date 오름차순)
        series: dict[str, list[tuple[int, float]]] = {}
        for tk, d_int, close in px_rows:
            series.setdefault(tk, []).append((int(d_int), float(close)))

        def _trend(ticker: str, rec_date: str) -> dict:
            seq = series.get(ticker)
            if not seq:
                return {"short": "neutral", "medium": "neutral", "long": "neutral"}
            rec_int = int(rec_date.replace("-", ""))
            # 추천일 인덱스 — 추천일 이상인 첫 행
            base_i = next((i for i, (d, _) in enumerate(seq) if d >= rec_int), None)
            if base_i is None:
                return {"short": "neutral", "medium": "neutral", "long": "neutral"}
            base_close = seq[base_i][1]
            if base_close <= 0:
                return {"short": "neutral", "medium": "neutral", "long": "neutral"}

            def _ret(offset: int) -> float | None:
                j = base_i + offset
                if j >= len(seq):
                    return None
                return (seq[j][1] - base_close) / base_close * 100

            return {
                "short":  _marker(_ret(5)),
                "medium": _marker(_ret(20)),
                "long":   _marker(_ret(60)),
            }

        # 3) 날짜별 그룹핑
        grouped: dict[str, list] = {}
        for d, rnk, ticker, nm, sector, score, tier, close, cur_close, cum_ret in rows:
            grouped.setdefault(d, []).append({
                "rank":                  int(rnk),
                "ticker":                ticker,
                "name":                  nm or ticker,
                "sector":                sector,
                "score":                 float(score) if score is not None else 0.0,
                "tier":                  tier,
                "recommend_price":       float(close) if close is not None else 0.0,
                "current_price":         float(cur_close) if cur_close is not None else None,
                "cumulative_return_pct": float(cum_ret) if cum_ret is not None else 0.0,
                "trend":                 _trend(ticker, d),
            })

        items = [{"date": d, "winners": grouped[d]} for d in sorted(grouped, reverse=True)]
        return {"model_version": ver, "items": items}

    return _cached("winners", fetch, ttl=600, days_back=days_back, top_k=top_k, model_version=ver)
