"""
routers/compare.py
==================
종목 비교 엔드포인트.

여러 종목의 ML 점수 이력 + 최신 재무 지표를 병렬로 조회하여
한 번에 비교 가능한 형태로 반환합니다.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services import data as svc

router = APIRouter(prefix="/compare", tags=["compare"])


class CompareFinance(BaseModel):
    per:            Optional[float] = None
    pbr:            Optional[float] = None
    roe:            Optional[float] = None
    debt_ratio:     Optional[float] = None
    op_margin:      Optional[float] = None
    rev_growth_yoy: Optional[float] = None
    finance_score:  Optional[float] = None
    year:           Optional[int]   = None
    quarter:        Optional[int]   = None


class CompareItem(BaseModel):
    ticker:          str
    name:            Optional[str]   = None
    sector:          Optional[str]   = None
    latest_score:    Optional[float] = None
    tier:            Optional[str]   = None
    score_history:   list[dict]      = []   # [{date, score}, ...]
    finance:         Optional[CompareFinance] = None


class CompareResponse(BaseModel):
    tickers:  list[str]
    total:    int
    items:    list[CompareItem]


@router.get("", response_model=CompareResponse, summary="종목 비교 (ML 점수 이력 + 재무)")
def compare_stocks(
    tickers:       str  = Query(..., description="쉼표 구분 티커 목록 (최대 10개). 예: 005930,000660"),
    model_version: str  = Query("latest", description="모델 버전"),
    period:        str  = Query("1y", description="점수 이력 기간: 3m | 6m | 1y | 3y | all"),
):
    """
    2~10개 종목의 ML 점수 이력과 최신 재무 요약을 비교합니다.

    - `score_history`: 기간 내 날짜별 ML 점수 [{date, score}, ...]
    - `finance`: 가장 최근 분기 재무 지표 요약
    """
    ticker_list = [t.strip().zfill(6) for t in tickers.split(",") if t.strip()]
    if len(ticker_list) < 2:
        raise HTTPException(status_code=422, detail="비교할 종목을 2개 이상 입력하세요.")
    if len(ticker_list) > 10:
        raise HTTPException(status_code=422, detail="종목은 최대 10개까지 비교할 수 있습니다.")

    PERIOD_DAYS = {"3m": 90, "6m": 180, "1y": 365, "3y": 1095, "all": 0}
    if period not in PERIOD_DAYS:
        raise HTTPException(status_code=422, detail=f"period는 {list(PERIOD_DAYS)} 중 하나여야 합니다.")

    try:
        rows = svc.compare_stocks(
            tickers=ticker_list,
            model_version=model_version,
            period_days=PERIOD_DAYS[period],
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    items = [CompareItem(**r) for r in rows]
    return CompareResponse(tickers=ticker_list, total=len(items), items=items)
