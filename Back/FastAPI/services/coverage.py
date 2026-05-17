"""
services/coverage.py
====================
W8 축소 — 신규 상장 60일 룰. 데이터 충분치 않은 종목을 추천에서 제외.

설계:
  - 신규 상장 종목이 추천 카드에 그냥 등장하면 사용자 신뢰 깎임.
  - prices 거래일 수 < 60 → "insufficient_data". 추천 결과에서 *제외*.
  - 응답 메타에 `coverage_excluded` 카운터 부착해 투명성 확보.
  - 임베딩 근접 추론 (08·차기_사이클.md §W8) 은 *컷* — W3.5 sector_proximity FAIL +
    W5 ablation embedding negative gain 으로 약한 신호. 60일 룰만 유지가 정직.

본 모듈은 *순수 함수* — DuckDB 의존은 `load_ticker_days` 에 격리.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

# B29: 신규 상장 종목 제외 기준 (영업일 수).
# 60 영업일 ≈ 3개월. 근거:
#   - IPO 후 2~4주 보호예수 + 초기 변동성 안정화 1~2개월 → 합산 ~3개월.
#   - ML 피처 중 rolling 60d momentum/vol 이 핵심 신호 → 60일 미만은 피처 신뢰도 ↓.
#   - 한국거래소 KOSPI200 편입 기준 (상장 후 6개월) 대비 절반 → 보수적 안전선.
# 운영 조정 필요 시 env COVERAGE_MIN_DAYS 로 override.
DEFAULT_MIN_DAYS = int(os.getenv("COVERAGE_MIN_DAYS", "60"))


def coverage_status(available_days: int, *, min_days: int = DEFAULT_MIN_DAYS) -> str:
    """available_days < min_days → 'insufficient_data', 아니면 'ok'."""
    return "ok" if available_days >= min_days else "insufficient_data"


def filter_insufficient_coverage(
    rows:        list[dict],
    ticker_days: dict[str, int],
    *,
    min_days:   int = DEFAULT_MIN_DAYS,
    ticker_key: str = "ticker",
) -> tuple[list[dict], int]:
    """
    rows 에서 ticker_days < min_days 인 항목 제거.
    반환: (남은_rows, 제외된_종목_수).

    ticker_days 에 *없는* ticker 는 *데이터 부재* 로 보고 제외 (안전 우선).
    """
    if not rows:
        return rows, 0
    kept: list[dict] = []
    excluded = 0
    for r in rows:
        t = r.get(ticker_key)
        if t is None:
            excluded += 1
            continue
        days = ticker_days.get(t)
        if days is None or days < min_days:
            excluded += 1
            continue
        kept.append(r)
    return kept, excluded


# ── DuckDB 어댑터 ──────────────────────────────────────────────────────────

def load_ticker_days(
    duckdb_path: str | Path,
    tickers:     Iterable[str],
    *,
    as_of_date:  Optional[str] = None,
) -> dict[str, int]:
    """
    각 ticker 의 *최근 1년 거래일 수* 조회. as_of_date 이전 데이터만 카운트.
    DuckDB prices.date 는 BIGINT(YYYYMMDD).
    """
    import duckdb

    tickers = list(tickers)
    if not tickers:
        return {}

    cutoff_int = None
    if as_of_date:
        cutoff_int = int(str(as_of_date).replace("-", ""))

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        tlist = ",".join(f"'{t}'" for t in tickers)
        where = [f"ticker IN ({tlist})"]
        if cutoff_int is not None:
            where.append(f"date <= {cutoff_int}")
        sql = f"""
            SELECT ticker, COUNT(*) AS days
            FROM prices
            WHERE {' AND '.join(where)}
            GROUP BY ticker
        """
        rows = con.execute(sql).fetchall()
    finally:
        con.close()

    return {t: int(d) for t, d in rows}
