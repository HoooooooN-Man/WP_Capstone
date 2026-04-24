"""
routers/screener.py
===================
다중 조건 종목 스크리너 엔드포인트.

ML 점수 + 재무 지표 조건을 조합하여 종목을 필터링합니다.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services import data as svc

router = APIRouter(prefix="/screener", tags=["screener"])


class ScreenerItem(BaseModel):
    ticker:         str
    name:           Optional[str]   = None
    sector:         Optional[str]   = None
    score:          Optional[float] = None
    tier:           Optional[str]   = None
    latest_date:    Optional[str]   = None
    per:            Optional[float] = None
    pbr:            Optional[float] = None
    roe:            Optional[float] = None
    debt_ratio:     Optional[float] = None
    op_margin:      Optional[float] = None
    rev_growth_yoy: Optional[float] = None
    finance_score:  Optional[float] = None
    composite_score: Optional[float] = None  # ML 60% + Finance 40%


class ScreenerResponse(BaseModel):
    total:  int
    items:  list[ScreenerItem]


@router.get("", response_model=ScreenerResponse, summary="다중 조건 종목 스크리너")
def screen_stocks(
    # ML 조건
    model_version:  str            = Query("latest", description="모델 버전"),
    min_score:      float          = Query(0.0, ge=0, le=100, description="최소 ML 점수"),
    tier:           Optional[str]  = Query(None, description="티어 필터: A | B | C | D"),
    sector:         Optional[str]  = Query(None, description="섹터 이름 (부분 일치)"),
    # 재무 조건
    max_per:        Optional[float] = Query(None, description="최대 PER"),
    max_pbr:        Optional[float] = Query(None, description="최대 PBR"),
    min_roe:        Optional[float] = Query(None, description="최소 ROE (%)"),
    max_debt_ratio: Optional[float] = Query(None, description="최대 부채비율 (%)"),
    min_op_margin:  Optional[float] = Query(None, description="최소 영업이익률 (%)"),
    min_rev_growth: Optional[float] = Query(None, description="최소 매출성장률 YoY (%)"),
    min_finance_score: Optional[float] = Query(None, ge=0, le=100, description="최소 재무 스코어"),
    # 정렬·페이지
    sort_by:        str            = Query("composite_score", description="정렬 기준: composite_score | score | finance_score | roe"),
    limit:          int            = Query(50, ge=1, le=200, description="최대 결과 수"),
):
    """
    ML 추천 점수 + 재무 지표를 복합 조건으로 종목을 검색합니다.

    **composite_score** = ML score × 0.6 + finance_score × 0.4
    """
    try:
        rows = svc.screen_stocks(
            model_version=model_version,
            min_score=min_score,
            tier=tier,
            sector=sector,
            max_per=max_per,
            max_pbr=max_pbr,
            min_roe=min_roe,
            max_debt_ratio=max_debt_ratio,
            min_op_margin=min_op_margin,
            min_rev_growth=min_rev_growth,
            min_finance_score=min_finance_score,
            sort_by=sort_by,
            limit=limit,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    items = [ScreenerItem(**r) for r in rows]
    return ScreenerResponse(total=len(items), items=items)
