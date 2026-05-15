"""
services/star_rating.py
=======================
P1-7 (PRD §8.1) — ML 점수에서 별점(0-5) + 동종 섹터 내 백분위 계산.

별점 변환:
  score ≥ 90 → 5.0★
  score ≥ 80 → 4.5★
  score ≥ 70 → 4.0★
  score ≥ 60 → 3.5★
  score ≥ 50 → 3.0★
  score ≥ 40 → 2.5★
  score ≥ 30 → 2.0★
  score ≥ 20 → 1.5★
  score ≥ 10 → 1.0★
  else       → 0.5★

백분위:
  동종 sector 내 score 기준 percentile (상위 N%).
  예: 상위 0.09% → "상위 0.09%" (choicestock 톤).
"""

from __future__ import annotations

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
    get_latest_date as _get_latest_date,
)


def score_to_stars(score: float | None) -> float:
    """0-100 점수 → 0.5 단위 별점 (0.5 ~ 5.0)."""
    if score is None:
        return 0.5
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 0.5
    thresholds = [(90, 5.0), (80, 4.5), (70, 4.0), (60, 3.5), (50, 3.0),
                  (40, 2.5), (30, 2.0), (20, 1.5), (10, 1.0)]
    for cutoff, stars in thresholds:
        if s >= cutoff:
            return stars
    return 0.5


def compute_sector_percentile(ticker: str, sector: str, score: float,
                              model_version: str, date: str) -> float | None:
    """sector 내 score 순위 → 상위 백분위 (1.0 = 상위 1%)."""
    if not sector or score is None:
        return None
    con = _con()
    row = con.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN score > ? THEN 1 ELSE 0 END) AS better
        FROM scores
        WHERE model_version=? AND CAST(date AS VARCHAR)=? AND sector=?
        """,
        [float(score), model_version, date, sector],
    ).fetchone()
    if not row or not row[0]:
        return None
    total = int(row[0])
    better = int(row[1] or 0)
    if total <= 0:
        return None
    return round((better + 1) / total * 100.0, 2)


def attach_star_ratings(items: list[dict], model_version: str = "latest") -> list[dict]:
    """추천/검색 결과에 star_rating + percentile_in_sector 부착."""
    ver = _resolve_version(model_version)
    date = _get_latest_date(ver)

    # 섹터별 score 분포를 한 번에 조회 (N+1 회피)
    con = _con()
    if date:
        try:
            sector_rows = con.execute(
                """
                SELECT sector, COUNT(*) AS total
                FROM scores
                WHERE model_version=? AND CAST(date AS VARCHAR)=?
                GROUP BY sector
                """,
                [ver, date],
            ).fetchall()
            sector_totals = {r[0]: int(r[1] or 0) for r in sector_rows}
        except Exception:
            sector_totals = {}
    else:
        sector_totals = {}

    for r in items:
        r["star_rating"] = score_to_stars(r.get("score"))
        sector = r.get("sector")
        score = r.get("score")
        if sector and score is not None and date and sector_totals.get(sector):
            try:
                better = con.execute(
                    """
                    SELECT COUNT(*) FROM scores
                    WHERE model_version=? AND CAST(date AS VARCHAR)=? AND sector=? AND score > ?
                    """,
                    [ver, date, sector, float(score)],
                ).fetchone()
                cnt_better = int(better[0] or 0)
                total = sector_totals[sector]
                r["percentile_in_sector"] = round((cnt_better + 1) / total * 100.0, 2)
                r["sector_total"] = total
                r["sector_rank"] = cnt_better + 1
            except Exception:
                pass
    return items
