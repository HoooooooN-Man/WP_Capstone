"""
schemas/finance.py
==================
재무 데이터 응답 스키마.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class FinanceItem(BaseModel):
    year:           int
    quarter:        int
    base_date:      Optional[str]   = None
    market_cap:     Optional[float] = None
    per:            Optional[float] = None
    pbr:            Optional[float] = None
    eps:            Optional[float] = None
    bps:            Optional[float] = None
    dps:            Optional[float] = None
    dividend_yield: Optional[float] = None
    op_margin:      Optional[float] = None
    net_margin:     Optional[float] = None
    roe:            Optional[float] = None
    debt_ratio:     Optional[float] = None
    current_ratio:  Optional[float] = None
    revenue:        Optional[float] = None
    op_profit:      Optional[float] = None
    net_profit:     Optional[float] = None
    equity:         Optional[float] = None
    total_debt:     Optional[float] = None
    current_assets: Optional[float] = None
    current_liab:   Optional[float] = None
    rev_growth_yoy: Optional[float] = None
    rev_growth_qoq: Optional[float] = None
    op_growth_yoy:  Optional[float] = None
    op_growth_qoq:  Optional[float] = None
    finance_score:  Optional[float] = None


class FinanceResponse(BaseModel):
    ticker:  str
    name:    Optional[str] = None
    total:   int
    items:   list[FinanceItem]


class FinanceLatest(BaseModel):
    """가장 최근 분기 재무 단건."""
    ticker:         str
    name:           Optional[str]   = None
    year:           Optional[int]   = None
    quarter:        Optional[int]   = None
    base_date:      Optional[str]   = None
    per:            Optional[float] = None
    pbr:            Optional[float] = None
    eps:            Optional[float] = None
    roe:            Optional[float] = None
    debt_ratio:     Optional[float] = None
    op_margin:      Optional[float] = None
    rev_growth_yoy: Optional[float] = None
    finance_score:  Optional[float] = None
