"""
schemas/chart.py
================
캔들스틱 + 이동평균 응답 스키마.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class CandleItem(BaseModel):
    date:       str
    open:       Optional[float] = None
    high:       Optional[float] = None
    low:        Optional[float] = None
    close:      Optional[float] = None
    volume:     Optional[float] = None
    amount:     Optional[float] = None
    market_cap: Optional[float] = None
    ma5:        Optional[float] = None
    ma20:       Optional[float] = None
    ma60:       Optional[float] = None
    ma120:      Optional[float] = None


class ChartResponse(BaseModel):
    ticker: str
    name:   Optional[str] = None
    period: str            # "1m" | "3m" | "6m" | "1y" | "3y" | "all"
    total:  int
    items:  list[CandleItem]
