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

# B9: 단일 ±3% 임계는 기간별로 부적합.
#   5일 ±3%  — 너무 넓음 (대부분 neutral)
#   20일 ±3% — 적절
#   60일 ±3% — 너무 좁음 (대부분 up/down)
# 기간별 임계 차등.
_TREND_THRESHOLDS = {
    5:  (1.5,  -1.5),   # 1주
    20: (5.0,  -5.0),   # 1개월
    60: (12.0, -12.0),  # 3개월 — 종목 통상 변동성 흡수
}
_TREND_DEFAULT = (3.0, -3.0)


def _marker(pct: float | None, period: int = 0) -> str:
    if pct is None:
        return "neutral"
    up_th, down_th = _TREND_THRESHOLDS.get(period, _TREND_DEFAULT)
    if pct > up_th:
        return "up"
    if pct < down_th:
        return "down"
    return "neutral"


def get_winners(days_back: int = 21, top_k: int = 5, model_version: str = "latest") -> dict:
    """최근 `days_back` 거래일의 일자별 Top-`top_k` 승부주.

    반환: {"model_version", "items": [{"date", "winners": [...]}, ...]}  (날짜 DESC)
    """
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()

        # B63 — 승부주 다중 필터:
        #   ① illiquid 제외: 최근 5거래일 평균 거래량 >= 1,000주
        #   ② 거품주 제외: PER > 100 OR PBR > 10 → 매수 의미 약함
        #   ③ 섹터 다양화: 동일 섹터 최대 2종목 (5종목 중)
        #   ④ split 의심: pool 단계는 score 만, attach 단계에서 NULL 처리 (B61)
        rows = con.execute(
            """
            WITH dates AS (
                SELECT DISTINCT CAST(date AS VARCHAR) AS d
                FROM scores WHERE model_version = ?
                ORDER BY d DESC LIMIT ?
            ),
            -- B63①: ticker 별 최근 5거래일 평균 거래량
            liq AS (
                SELECT ticker, AVG(volume) AS avg_vol_5d
                FROM (
                    SELECT ticker, volume,
                        ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
                    FROM prices
                ) WHERE rn <= 5
                GROUP BY ticker
            ),
            -- B63②: ticker 별 최신 finance per/pbr (거품 검사)
            latest_fin AS (
                SELECT f.ticker, f.per, f.pbr
                FROM finance f
                INNER JOIN (
                    SELECT ticker, MAX(year*10+quarter) AS yq
                    FROM finance WHERE per IS NOT NULL OR pbr IS NOT NULL
                    GROUP BY ticker
                ) m ON f.ticker=m.ticker AND f.year*10+f.quarter=m.yq
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
                LEFT JOIN liq         ON s.ticker = liq.ticker
                LEFT JOIN latest_fin lf ON s.ticker = lf.ticker
                WHERE s.model_version = ?
                  AND CAST(s.date AS VARCHAR) IN (SELECT d FROM dates)
                  AND COALESCE(liq.avg_vol_5d, 0) >= 1000          -- ① illiquid 제외
                  AND COALESCE(lf.per, 0) <= 100                   -- ② PER 거품 제외
                  AND COALESCE(lf.pbr, 0) <= 10                    -- ② PBR 거품 제외
            ),
            -- B63③: 섹터 다양화 — 동일 섹터 내 score DESC 순위 + 일자 내 전체 score DESC 순위.
            -- 일자 내 종합 순위는 우선순위 1: 전체 score 상위, 우선순위 2: 섹터 내 첫 종목 우대.
            with_ranks AS (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY d, sector ORDER BY score DESC, ticker) AS sec_rnk,
                    ROW_NUMBER() OVER (PARTITION BY d ORDER BY score DESC, ticker) AS all_rnk
                FROM dedup
            ),
            -- 섹터당 max 2종목 (sec_rnk <= 2) 만 통과
            sec_filtered AS (
                SELECT * FROM with_ranks WHERE sec_rnk <= 2
            ),
            -- 최종 top_k 선정: score 정렬
            ranked AS (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY d ORDER BY score DESC, ticker) AS rnk
                FROM sec_filtered
            ),
            win AS (SELECT * FROM ranked WHERE rnk <= ?),
            latest_px AS (
                SELECT ticker, close, date FROM (
                    SELECT ticker, close, date,
                           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) rn
                    FROM prices
                ) WHERE rn = 1
            )
            SELECT
                w.d, w.rnk, w.ticker, w.nm, w.sector, w.score, w.tier, w.close,
                lp.close AS cur_close,
                CAST(lp.date AS VARCHAR) AS cur_date,
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

            # B9: period 정보 전달 → 기간별 임계 적용.
            return {
                "short":  _marker(_ret(5),  period=5),
                "medium": _marker(_ret(20), period=20),
                "long":   _marker(_ret(60), period=60),
            }

        # 3) 날짜별 그룹핑
        # current_price 가 stale (가장 최신 거래일이 scores 최신 날짜보다 5일+ 과거) 인 경우
        # FE 가 표시할지 결정할 수 있도록 `current_price_as_of` + `is_stale` 명시.
        # B62 - 목표가: fair_value API 한 번 호출해 ticker 별 적정가 매핑.
        from .fairvalue_svc import get_fair_value as _get_fv
        target_map: dict[str, float] = {}
        for tk in tickers:
            try:
                fv = _get_fv(tk)
                if fv and fv.get("fair_value"):
                    target_map[tk] = float(fv["fair_value"])
            except Exception:
                continue

        scores_latest_int = max(int(r[0].replace("-", "")) for r in rows) if rows else 0
        grouped: dict[str, list] = {}
        for d, rnk, ticker, nm, sector, score, tier, close, cur_close, cur_date, cum_ret in rows:
            cur_date_int = int(cur_date) if cur_date else 0
            # 5 거래일 이상 차이 → stale (거래정지·신규상장 직전 등)
            is_stale = bool(cur_date) and (scores_latest_int - cur_date_int) > 5
            grouped.setdefault(d, []).append({
                "rank":                  int(rnk),
                "ticker":                ticker,
                "name":                  nm or ticker,
                "sector":                sector,
                "score":                 float(score) if score is not None else 0.0,
                "tier":                  tier,
                "recommend_price":       float(close) if close is not None else 0.0,
                "current_price":         float(cur_close) if cur_close is not None else None,
                "current_price_as_of":   cur_date if cur_date else None,
                "current_price_is_stale": is_stale,
                "cumulative_return_pct": float(cum_ret) if cum_ret is not None else 0.0,
                "trend":                 _trend(ticker, d),
                # B62: 적정주가 (fairvalue API). None 이면 FE 가 "-" 표시.
                "target_price":          target_map.get(ticker),
            })

        items = [{"date": d, "winners": grouped[d]} for d in sorted(grouped, reverse=True)]
        return {"model_version": ver, "items": items}

    return _cached("winners", fetch, ttl=600, days_back=days_back, top_k=top_k, model_version=ver)
