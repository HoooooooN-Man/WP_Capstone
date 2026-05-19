"""
services/_helpers.py
====================
서비스 레이어 공통 유틸 — 중복 제거 (2026-05-19).

각 서비스 파일에 자체 정의돼 있던 헬퍼들을 한 곳으로:
  - mark_bubble_stock : per/pbr 거품 마킹 (PER>100 OR PBR>10 → fair_band='very_overvalued')
  - parse_yyyymmdd    : "20260101" / "2026-01-01" → datetime
  - to_date_int       : "2026-01-01" → 20260101

이전 분산 정의:
  - scores_svc.py L258-260, L704-706, L836-838 (3중)
  - outcomes_svc.py L92-97 (_parse_date), L201-205 (_parse)
  - winners_svc.py L153-154 (_parse_d)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


# ─────────────────────────────────────────────────────────────────
# 거품주 마킹 (B54/B64/B64-bis 동일 룰)
# ─────────────────────────────────────────────────────────────────
PER_BUBBLE_THRESHOLD: float = 100.0
PBR_BUBBLE_THRESHOLD: float = 10.0


def mark_bubble_stock(row: dict) -> None:
    """row 의 per/pbr 검사 후 거품이면 fair_band='very_overvalued' 마킹 (in-place).

    PER > 100 또는 PBR > 10 = 매우 거품 → 매수 신호 차단 (signal_label 이 WATCH 처리).
    값이 None 이거나 변환 실패 시 graceful pass.
    """
    per_v = row.get("per")
    pbr_v = row.get("pbr")
    try:
        if (per_v is not None and float(per_v) > PER_BUBBLE_THRESHOLD) or \
           (pbr_v is not None and float(pbr_v) > PBR_BUBBLE_THRESHOLD):
            row["fair_band"] = "very_overvalued"
    except (TypeError, ValueError):
        pass


def mark_bubble_stocks(rows: list[dict]) -> list[dict]:
    """rows 전체에 mark_bubble_stock 적용 (in-place)."""
    for r in rows:
        mark_bubble_stock(r)
    return rows


# ─────────────────────────────────────────────────────────────────
# 날짜 파싱 (DuckDB YYYYMMDD ↔ datetime)
# ─────────────────────────────────────────────────────────────────
def parse_yyyymmdd(s: Optional[str]) -> Optional[datetime]:
    """YYYYMMDD ("20260101") 또는 YYYY-MM-DD ("2026-01-01") → datetime.

    DuckDB 의 scores.date / prices.date 는 BIGINT 이고 CAST(... AS VARCHAR) 결과는
    "20260429" 형식 (하이픈 없음). market_indices.date 는 DATE 라 "2026-04-29" 형식.
    두 포맷 모두 허용. 비정상 입력 (None, 빈 문자열, 비숫자) 은 None 반환 (graceful).
    """
    if not s:
        return None
    s = s.replace("-", "")
    if not s.isdigit() or len(s) != 8:
        return None
    try:
        return datetime.strptime(s, "%Y%m%d")
    except ValueError:
        return None


def to_date_int(s: Optional[str]) -> Optional[int]:
    """YYYY-MM-DD 또는 YYYYMMDD → 20260101 (int)."""
    if not s:
        return None
    s = s.replace("-", "")
    if not s.isdigit() or len(s) != 8:
        return None
    return int(s)
