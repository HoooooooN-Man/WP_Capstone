"""
schemas/portfolio.py
====================
마켓 레이더(시장 기상도) + KOSPI200 포트폴리오 응답 스키마.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel


# ── 마켓 레이더 ────────────────────────────────────────────────────────────────

class MarketRegimeResponse(BaseModel):
    """시장 국면(기상도) 응답."""
    date:          str
    model_version: str
    total_count:   int                              # 해당 날짜 전체 종목 수
    tier_a_count:  int                              # Tier A 종목 수
    tier_a_ratio:  float                            # Tier A 비율 (%)
    status:        Literal["greed", "neutral", "fear"]
    weather:       Literal["맑음", "흐림", "비"]
    message:       str


# ── KOSPI 200 포트폴리오 ───────────────────────────────────────────────────────

class PortfolioItem(BaseModel):
    """포트폴리오 구성 종목 단건."""
    rank:          int
    ticker:        str
    name:          Optional[str]   = None
    sector:        Optional[str]   = None
    score:         float
    tier:          str
    pbr:           Optional[float] = None           # stable 타입에서만 반환


class PortfolioResponse(BaseModel):
    """KOSPI200 자동 포트폴리오 응답."""
    type:          Literal["growth", "stable"]
    date:          str
    model_version: str
    total:         int
    items:         list[PortfolioItem]
