"""
services/fairvalue_svc.py
=========================
P2-13 (PRD §8.1) — 적정주가(Fair Value) 밴드차트.

설계 — 별도 ML 학습 없이 multiple 기반 추정. finance 테이블의 PER/PBR/EPS/BPS 활용:

  1. 동일 섹터의 PER·PBR 중앙값 추출 (시장 anchor)
  2. 종목 자체 4분기 PER·PBR 중앙값 추출 (자기 anchor)
  3. 적정가 = 평균(sector PER × EPS, sector PBR × BPS, 자기 PER × EPS, 자기 PBR × BPS)
  4. 현재가 vs 적정가 → 5단계 색대:
       deviation = (current - fair) / fair
       ≤ -30% → 매우저평가  (very_undervalued)
       ≤ -10% → 저평가      (undervalued)
       ≤ +10% → 적정        (fair)
       ≤ +30% → 고평가      (overvalued)
        >+30% → 매우고평가  (very_overvalued)

캡스톤 가이드: 룰 기반·투명·재현 가능. 실거래 자문 아님 (PRD §9 면책).
"""

from __future__ import annotations

from typing import Optional

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
    get_latest_date as _get_latest_date,
)


VALUATION_BANDS = [
    ("very_undervalued", "매우저평가", -1.00, -0.30),
    ("undervalued",      "저평가",     -0.30, -0.10),
    ("fair",             "적정",       -0.10,  0.10),
    ("overvalued",       "고평가",      0.10,  0.30),
    ("very_overvalued",  "매우고평가",   0.30,  1.00),
]


def classify_valuation(deviation: float) -> dict:
    """deviation (= (current - fair) / fair) → 5단계 라벨."""
    try:
        d = float(deviation)
    except (TypeError, ValueError):
        d = 0.0

    for code, ko, lo, hi in VALUATION_BANDS:
        if lo <= d < hi:
            return {"band": code, "band_ko": ko, "deviation": round(d * 100, 2)}
    # 경계값 처리 — deviation ≥ +30%
    return {"band": "very_overvalued", "band_ko": "매우고평가", "deviation": round(d * 100, 2)}


def compute_fair_value(
    eps: float | None,
    bps: float | None,
    sector_per: float | None,
    sector_pbr: float | None,
    self_per: float | None,
    self_pbr: float | None,
) -> Optional[float]:
    """4가지 추정치의 평균 — None/0 항목은 자동 제외."""
    estimates = []
    if eps is not None and sector_per is not None and sector_per > 0 and eps > 0:
        estimates.append(eps * sector_per)
    if bps is not None and sector_pbr is not None and sector_pbr > 0 and bps > 0:
        estimates.append(bps * sector_pbr)
    if eps is not None and self_per is not None and self_per > 0 and eps > 0:
        estimates.append(eps * self_per)
    if bps is not None and self_pbr is not None and self_pbr > 0 and bps > 0:
        estimates.append(bps * self_pbr)
    if not estimates:
        return None
    return sum(estimates) / len(estimates)


def get_fair_value(ticker: str) -> Optional[dict]:
    """단건 — 종목의 현재가 + 적정가 + 5단계 분류 + 추정 근거."""
    t = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()

        # 현재가 (prices 최신 종가)
        cur = con.execute(
            """
            SELECT close, CAST(date AS VARCHAR) FROM prices
            WHERE ticker=? ORDER BY date DESC LIMIT 1
            """,
            [t],
        ).fetchone()
        if not cur:
            return None
        current_price = float(cur[0] or 0)
        current_date = cur[1]

        # 종목의 최신 분기 재무 + 섹터
        fin = con.execute(
            """
            SELECT
                f.eps, f.bps, f.per, f.pbr,
                COALESCE(st.wics_large_name, st.wics_mid_name) AS sector,
                st.name
            FROM finance f
            LEFT JOIN stocks st ON f.ticker = st.ticker
            WHERE f.ticker = ?
              AND f.eps IS NOT NULL AND f.bps IS NOT NULL
            ORDER BY f.year DESC, f.quarter DESC
            LIMIT 1
            """,
            [t],
        ).fetchone()
        if not fin:
            return None
        eps, bps, _self_per, _self_pbr, sector, name = fin

        # 자기 4분기 PER/PBR 중앙값 (이상치 완화)
        self_med = con.execute(
            """
            SELECT
                MEDIAN(per)  FILTER (WHERE per  > 0) AS self_per,
                MEDIAN(pbr)  FILTER (WHERE pbr  > 0) AS self_pbr
            FROM finance
            WHERE ticker = ?
              AND per IS NOT NULL AND pbr IS NOT NULL
            """,
            [t],
        ).fetchone()
        self_per_med = float(self_med[0]) if self_med and self_med[0] is not None else None
        self_pbr_med = float(self_med[1]) if self_med and self_med[1] is not None else None

        # 섹터 PER/PBR 중앙값 (최신 분기)
        sector_per = sector_pbr = None
        if sector:
            sec = con.execute(
                """
                SELECT
                    MEDIAN(f.per) FILTER (WHERE f.per > 0 AND f.per < 200) AS sec_per,
                    MEDIAN(f.pbr) FILTER (WHERE f.pbr > 0 AND f.pbr < 30)  AS sec_pbr
                FROM finance f
                LEFT JOIN stocks st ON f.ticker = st.ticker
                WHERE COALESCE(st.wics_large_name, st.wics_mid_name) = ?
                  AND (f.year, f.quarter) IN (
                      SELECT f2.year, f2.quarter FROM finance f2
                      WHERE f2.ticker = ?
                      ORDER BY f2.year DESC, f2.quarter DESC LIMIT 1
                  )
                """,
                [sector, t],
            ).fetchone()
            sector_per = float(sec[0]) if sec and sec[0] is not None else None
            sector_pbr = float(sec[1]) if sec and sec[1] is not None else None

        fair = compute_fair_value(
            eps=float(eps) if eps else None,
            bps=float(bps) if bps else None,
            sector_per=sector_per,
            sector_pbr=sector_pbr,
            self_per=self_per_med,
            self_pbr=self_pbr_med,
        )
        if fair is None or fair <= 0:
            return None

        deviation = (current_price - fair) / fair
        band = classify_valuation(deviation)

        return {
            "ticker":         t,
            "name":           name,
            "sector":         sector,
            "current_price":  round(current_price, 2),
            "current_date":   current_date,
            "fair_value":     round(fair, 2),
            "deviation_pct":  band["deviation"],
            "band":           band["band"],
            "band_ko":        band["band_ko"],
            "inputs": {
                "eps":         float(eps) if eps else None,
                "bps":         float(bps) if bps else None,
                "sector_per":  round(sector_per, 2) if sector_per else None,
                "sector_pbr":  round(sector_pbr, 2) if sector_pbr else None,
                "self_per_med": round(self_per_med, 2) if self_per_med else None,
                "self_pbr_med": round(self_pbr_med, 2) if self_pbr_med else None,
            },
            "method":         "multiple_based",
            "is_advice":      False,
        }

    return _cached("fair_value", fetch, ttl=3600, ticker=t)


def get_fair_value_history(ticker: str, periods: int = 12) -> list[dict]:
    """월별 종가 vs 적정가 이력 (밴드차트용).

    분기별 finance + 월말 prices 종가 매칭. 캡스톤에서는 최근 N 분기만.
    """
    t = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()

        # 분기 finance + 분기 말일 종가 매칭
        rows = con.execute(
            """
            WITH q AS (
                SELECT year, quarter, eps, bps, per, pbr, base_date
                FROM finance
                WHERE ticker = ? AND eps IS NOT NULL AND bps IS NOT NULL
                ORDER BY year DESC, quarter DESC
                LIMIT ?
            )
            SELECT
                q.year, q.quarter, q.eps, q.bps, q.per, q.pbr,
                CAST(q.base_date AS VARCHAR) AS bdate,
                (
                    SELECT close FROM prices
                    WHERE ticker = ? AND date <= q.base_date
                    ORDER BY date DESC LIMIT 1
                ) AS close
            FROM q
            ORDER BY q.year ASC, q.quarter ASC
            """,
            [t, periods, t],
        ).fetchall()

        result = []
        for year, quarter, eps, bps, per, pbr, bdate, close in rows:
            # 단순 추정: 자기 PER × EPS 와 자기 PBR × BPS 평균
            ests = []
            if eps and per and per > 0:
                ests.append(float(eps) * float(per))
            if bps and pbr and pbr > 0:
                ests.append(float(bps) * float(pbr))
            if not ests or not close:
                continue
            fair = sum(ests) / len(ests)
            dev = (float(close) - fair) / fair if fair > 0 else 0
            band = classify_valuation(dev)
            result.append({
                "year":           int(year),
                "quarter":        int(quarter),
                "date":           bdate[:10] if bdate else None,
                "close":          round(float(close), 2),
                "fair_value":     round(fair, 2),
                "deviation_pct":  band["deviation"],
                "band":           band["band"],
                "band_ko":        band["band_ko"],
            })
        return result

    return _cached("fair_value_history", fetch, ttl=3600, ticker=t, periods=periods)
