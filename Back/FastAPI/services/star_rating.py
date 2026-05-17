"""
services/star_rating.py
=======================
P1-7 (PRD §8.1) — ML 점수에서 별점(0-5) + 동종 섹터 내 백분위 계산.

B5 fix (스코어 절대값 한계 인정):
  scores.score 자체가 매일 백분위로 강제 분포 → "5★" 종목 수가 매일 거의 동일.
  이를 보완해 **score + sector_percentile** 두 축으로 별점 부여:
    - score 90+ AND sector 상위 5% → 5.0★ (절대+상대 모두 최고)
    - score 90+ → 4.5★
    - score 80+ → 4.0★
    - ...
  단순 score-only fallback 도 유지 (sector 없는 종목).

B6 fix (N+1 제거):
  이전 attach_star_ratings 가 ticker 마다 sector COUNT 쿼리 호출 → 50종목 = 50쿼리.
  윈도우 함수 한 번으로 모든 종목의 sector rank 를 dict 로 받아 O(1) lookup.
"""

from __future__ import annotations

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
    get_latest_date as _get_latest_date,
)


def score_to_stars(
    score: float | None,
    sector_pctile: float | None = None,
    tier: str | None = None,
    fair_band: str | None = None,
) -> float:
    """0-100 점수 → 0.5 단위 별점 (0.5 ~ 5.0). multi-factor.

    B56 (2026-05-17): 5★ 희소성 확보.
      이전: A티어 (백분위 상위 20%) + sector 상위 5% → 5★ = universe 1% 매일 ~23종목.
      새: 5★ = tier A (절대 prob 임계) AND sector 상위 1% AND fair_band 우호 → ~0.2% (5종목).
      4.5★ = tier A AND (sector 상위 5% OR score 90+).
      나머지는 score 기반.
    """
    if score is None:
        return 0.5
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 0.5

    t = (tier or "").strip().upper()
    band = (fair_band or "").strip().lower() or None

    # 절대 점수 베이스 (0.5 ~ 4.0)
    thresholds = [(90, 4.0), (80, 3.5), (70, 3.0), (60, 2.5), (50, 2.0),
                  (40, 1.5), (30, 1.0)]
    stars = 0.5
    for cutoff, st in thresholds:
        if s >= cutoff:
            stars = st
            break

    # 4.5★ 보너스 — tier A AND (sector 상위 5% OR score 90+).
    if t == "A" and (s >= 90 or (sector_pctile is not None and sector_pctile <= 5.0)):
        stars = max(stars, 4.5)

    # 5.0★ 최고 — tier A AND sector 상위 1% AND 거품 아님.
    if t == "A" and sector_pctile is not None and sector_pctile <= 1.0 \
       and band != "very_overvalued":
        stars = 5.0

    return stars


def attach_star_ratings(items: list[dict], model_version: str = "latest") -> list[dict]:
    """추천/검색 결과에 star_rating + percentile_in_sector 부착.

    B6: 윈도우 함수로 한 번에 모든 종목의 sector rank 계산. 이전 ticker 당 SELECT 제거.
    """
    if not items:
        return items
    ver = _resolve_version(model_version)
    date = _get_latest_date(ver)

    sector_data: dict[tuple[str, str], tuple[int, int]] = {}   # (sector, ticker) → (rank, total)
    if date:
        try:
            con = _con()
            rows = con.execute(
                """
                SELECT
                    sector,
                    ticker,
                    RANK() OVER (PARTITION BY sector ORDER BY score DESC) AS sec_rank,
                    COUNT(*) OVER (PARTITION BY sector)                    AS sec_total
                FROM scores
                WHERE model_version=? AND CAST(date AS VARCHAR)=?
                  AND sector IS NOT NULL
                """,
                [ver, date],
            ).fetchall()
            for sector, ticker, rk, tot in rows:
                sector_data[(sector, ticker)] = (int(rk), int(tot))
        except Exception:
            sector_data = {}

    for r in items:
        sector = r.get("sector")
        ticker = r.get("ticker")
        score = r.get("score")
        pctile: float | None = None
        key = (sector, ticker) if sector and ticker else None
        if key and key in sector_data:
            rk, tot = sector_data[key]
            r["sector_rank"]  = rk
            r["sector_total"] = tot
            pctile = round(rk / tot * 100.0, 2) if tot else None
            r["percentile_in_sector"] = pctile
        r["star_rating"] = score_to_stars(
            score, sector_pctile=pctile,
            tier=r.get("tier"), fair_band=r.get("fair_band"),
        )
    return items
