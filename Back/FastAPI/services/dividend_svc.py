"""
services/dividend_svc.py
========================
P2-14 (PRD §8.1) — 배당스코어 + 배당 이력 + 투자포인트.

5 항목 점수화 (각 0-100, 평균 = 종합 배당스코어):

  1. 배당수익률 (yield_score)
       dividend_yield (%) → 0-100
       4% 이상 → 100, 0% → 0, 선형 보간

  2. 연속배당 (consecutive_score)
       최근 N년 dps > 0 인 연수
       10년+ → 100, 0 → 0

  3. 배당금 인상 (growth_score)
       최근 2년간 dps 증가 비율
       +10%/년 이상 → 100, 음수 → 50 미만

  4. 배당성향 (payout_score)
       payout = dps / eps × 100
       30~70% → 100 (sweet spot), 그 외 감점

  5. EPS 성장률 (eps_growth_score)
       finance.rev_growth_yoy 활용 (proxy)
       +15%+ → 100

투자포인트는 종합 스코어에 따라 텍스트 자동 생성.
"""

from __future__ import annotations

from typing import Optional

from ._core import (
    con as _con,
    cached as _cached,
)


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _yield_score(yield_pct: float | None) -> float:
    if yield_pct is None:
        return 0.0
    try:
        y = float(yield_pct)
    except (TypeError, ValueError):
        return 0.0
    # 0% → 0, 4%+ → 100 선형
    return round(_clamp(y / 4.0 * 100.0), 1)


def _consecutive_score(years_paid: int) -> float:
    # 10년+ → 100
    return round(_clamp(years_paid / 10.0 * 100.0), 1)


def _growth_score(growth_yoy: float | None) -> float:
    """dps 전년 대비 증가율 (%, 예: 0.10 = 10%)."""
    if growth_yoy is None:
        return 50.0
    try:
        g = float(growth_yoy)
    except (TypeError, ValueError):
        return 50.0
    # +10%/년 이상 → 100, -10% → 0, 0% → 50
    return round(_clamp((g + 0.10) / 0.20 * 100.0), 1)


def _payout_score(payout_pct: float | None) -> float:
    """dps/eps (%) — 30~70% 가 sweet spot."""
    if payout_pct is None:
        return 50.0
    try:
        p = float(payout_pct)
    except (TypeError, ValueError):
        return 50.0
    if 30 <= p <= 70:
        return 100.0
    if p < 30:
        return round(_clamp(p / 30.0 * 80.0), 1)   # 0~80 사이
    if p > 70:
        # 70%+ — 감점 (80%+ 위험)
        return round(_clamp(100.0 - (p - 70.0) * 2.0), 1)
    return 50.0


def _eps_growth_score(growth_yoy: float | None) -> float:
    if growth_yoy is None:
        return 50.0
    try:
        g = float(growth_yoy)
    except (TypeError, ValueError):
        return 50.0
    # +15%+ → 100, -15% → 0
    return round(_clamp((g + 0.15) / 0.30 * 100.0), 1)


def _investment_point(total: float, consecutive: int, yield_pct: float) -> list[str]:
    """종합 스코어 → 투자포인트 문구 1-3개."""
    points = []
    if total >= 80:
        points.append("배당 안정성과 성장성을 동시에 갖춘 우량 배당주")
    elif total >= 60:
        points.append("배당 매력이 양호한 종목 — 중기 보유 적합")
    elif total >= 40:
        points.append("선별적 접근 권장 — 성장보다 안정성 우선 검토")
    else:
        points.append("배당 매력 제한적 — 시세 차익 위주 종목")

    if consecutive >= 10:
        points.append(f"{consecutive}년 연속 배당 지급 — 안정적 배당 정책")
    if yield_pct >= 3.0:
        points.append(f"배당수익률 {yield_pct:.2f}% — 인컴 투자 대상으로 적합")
    return points


def get_dividend_score(ticker: str) -> Optional[dict]:
    """종목 배당스코어 + 5항목 점수 + 이력."""
    t = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()

        # 최신 분기 — yield, dps, eps, rev_growth
        latest = con.execute(
            """
            SELECT year, quarter, dividend_yield, dps, eps, rev_growth_yoy
            FROM finance
            WHERE ticker = ? AND dps IS NOT NULL
            ORDER BY year DESC, quarter DESC
            LIMIT 1
            """,
            [t],
        ).fetchone()
        if not latest:
            return None
        _, _, yield_pct, dps, eps, rev_g = latest
        yield_pct = float(yield_pct) if yield_pct is not None else 0.0
        dps = float(dps) if dps is not None else 0.0
        eps = float(eps) if eps else None

        # 연속배당 — 최근 N분기 (4 = 1년) 중 dps > 0 인 연 수
        years = con.execute(
            """
            SELECT year, MAX(dps) AS yearly_dps
            FROM finance
            WHERE ticker = ?
            GROUP BY year
            ORDER BY year DESC
            """,
            [t],
        ).fetchall()
        years_paid = 0
        # 연속 카운트 (가장 최근부터 끊기는 시점까지)
        for y, ydps in years:
            if ydps is not None and float(ydps) > 0:
                years_paid += 1
            else:
                break

        # 배당금 인상 — 최근 2년 dps 비교
        dps_growth = None
        if len(years) >= 2 and years[1][1]:
            prev = float(years[1][1])
            cur = float(years[0][1] or 0)
            if prev > 0:
                dps_growth = (cur - prev) / prev

        # 배당성향
        payout_pct = (dps / eps * 100.0) if (eps and eps > 0 and dps > 0) else None

        # rev_growth_yoy 는 비율 (예: 0.15) 또는 % (예: 15) 둘 다 가능 — 가정 비율
        if rev_g is not None and abs(float(rev_g)) > 5:
            # 5 초과면 % 단위로 가정 → 비율로 변환
            rev_g_ratio = float(rev_g) / 100.0
        else:
            rev_g_ratio = float(rev_g) if rev_g is not None else None

        # 5항목 점수
        scores = {
            "yield_score":         _yield_score(yield_pct),
            "consecutive_score":   _consecutive_score(years_paid),
            "growth_score":        _growth_score(dps_growth),
            "payout_score":        _payout_score(payout_pct),
            "eps_growth_score":    _eps_growth_score(rev_g_ratio),
        }
        total = round(sum(scores.values()) / 5.0, 1)

        return {
            "ticker":            t,
            "dividend_score":    total,
            "scores":            scores,
            "yield_pct":         round(yield_pct, 2),
            "dps":               round(dps, 2),
            "years_paid":        years_paid,
            "dps_growth_yoy":    round(dps_growth, 4) if dps_growth is not None else None,
            "payout_pct":        round(payout_pct, 2) if payout_pct is not None else None,
            "investment_points": _investment_point(total, years_paid, yield_pct),
            "is_advice":         False,
        }

    return _cached("dividend_score", fetch, ttl=3600, ticker=t)


def get_dividend_history(ticker: str, years: int = 10) -> list[dict]:
    """연도별 배당 이력 — yield_pct / dps / payout_pct."""
    t = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()
        rows = con.execute(
            """
            SELECT
                year,
                MAX(dividend_yield) AS yield_pct,
                MAX(dps)            AS dps,
                AVG(eps)            AS eps_avg
            FROM finance
            WHERE ticker = ?
            GROUP BY year
            ORDER BY year DESC
            LIMIT ?
            """,
            [t, years],
        ).fetchall()
        result = []
        for y, ypct, dps, eps in rows:
            payout = None
            if dps is not None and eps and float(eps) > 0:
                payout = round(float(dps) / float(eps) * 100.0, 2)
            result.append({
                "year":       int(y),
                "yield_pct":  round(float(ypct), 4) if ypct is not None else None,
                "dps":        round(float(dps), 2) if dps is not None else None,
                "payout_pct": payout,
            })
        # 오름차순 (차트 표시용)
        result.reverse()
        return result

    return _cached("dividend_history", fetch, ttl=3600, ticker=t, years=years)
