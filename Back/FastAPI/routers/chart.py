"""
routers/chart.py
================
캔들스틱 차트 데이터 엔드포인트.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..services import data as svc
from ..schemas.chart import ChartResponse, CandleItem

router = APIRouter(prefix="/chart", tags=["chart"])

VALID_PERIODS = {"1m", "3m", "6m", "1y", "3y", "all"}


@router.get("/{ticker}", response_model=ChartResponse, summary="종목 캔들스틱 + 이동평균 데이터")
def get_chart(
    ticker: str,
    period: str = Query("1y", description="기간: 1m | 3m | 6m | 1y | 3y | all"),
):
    """
    지정 종목의 OHLCV + MA(5/20/60/120) 데이터를 반환합니다.

    - **period**: `1m`(1개월) `3m` `6m` `1y`(기본) `3y` `all`
    """
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=422,
            detail=f"period는 {sorted(VALID_PERIODS)} 중 하나여야 합니다.",
        )

    try:
        result = svc.get_chart(ticker=ticker, period=period)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not result:
        raise HTTPException(status_code=404, detail=f"종목 {ticker} 차트 데이터를 찾을 수 없습니다.")

    items = [CandleItem(**r) for r in result["items"]]
    return ChartResponse(
        ticker=result["ticker"],
        name=result.get("name"),
        period=period,
        total=len(items),
        items=items,
    )
