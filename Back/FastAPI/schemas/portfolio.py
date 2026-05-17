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
    """시장 국면(기상도) 응답.

    P0-4 (PRD §8.1): 5단계 라벨 + 0-100 마켓스코어. choicestock 벤치마크 호환.
    기존 3단계 status(greed/neutral/fear)는 5단계(panic/pessimism/neutral/optimism/greed)로 확장.
    """
    date:          str
    model_version: str
    total_count:   int
    tier_a_count:  int
    tier_a_ratio:  float
    daily_change:  Optional[float] = None
    status:        Literal["panic", "pessimism", "neutral", "optimism", "greed"]
    status_ko:     str
    weather:       str
    mood:          str
    market_score:  float
    score_range:   str
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
    sector_pbr_med: Optional[float] = None          # B12: 섹터 상대 비교용


class PortfolioResponse(BaseModel):
    """KOSPI200 자동 포트폴리오 응답."""
    type:          Literal["growth", "stable"]
    date:          str
    model_version: str
    total:         int
    items:         list[PortfolioItem]
    # B13: 진짜 KOSPI200 지수가 아니라 KOSPI 전체임을 응답에 명시.
    universe:      Optional[str]   = None
    universe_note: Optional[str]   = None
