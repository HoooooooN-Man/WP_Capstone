"""
schemas/portfolio.py
====================
마켓 레이더(시장 기상도) + KOSPI200 포트폴리오 응답 스키마.
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel


# ── 마켓 레이더 ────────────────────────────────────────────────────────────────

class MarketRegimeResponse(BaseModel):
    """시장 국면(기상도) 응답."""
    date:          str
    model_version: str
    total_count:   int                              # 해당 날짜 전체 종목 수
    tier_a_count:  int                              # Tier A 종목 수
    tier_a_ratio:  float                            # Tier A 비율 (%)
    status:        str                              # panic|pessimism|neutral|optimism|greed (+legacy fear)
    weather:       str
    message:       str
    # ── Front_v2 호환 (Optional) ─────────────────────────────────────────────
    status_ko:     Optional[str]   = None
    mood:          Optional[str]   = None
    market_score:  Optional[float] = None
    score_range:   Optional[str]   = None
    daily_change:  Optional[float] = None
    # ── v2 하이브리드 진단 필드 (Optional) ─────────────────────────────────
    regime:         Optional[str]            = None  # bull|sideways|bear
    regime_base:    Optional[float]          = None  # 30 / 50 / 70
    kospi_1m:       Optional[float]          = None  # KOSPI 1개월 변동률 (%)
    buy_count:      Optional[int]            = None  # BUY 시그널 종목 수
    avg_prob:       Optional[float]          = None  # 평균 prob_ensemble
    components:     Optional[Dict[str, Any]] = None  # c1 / c2 / c3
    adjustment:     Optional[float]          = None  # 합산 보정 (±15)
    score_version:  Optional[str]            = None  # v2_hybrid


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
