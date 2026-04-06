"""
routers/finance.py
==================
재무 데이터 엔드포인트.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..services import data as svc
from ..schemas.finance import FinanceResponse, FinanceItem, FinanceLatest

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/{ticker}", response_model=FinanceResponse, summary="종목 전체 재무 이력")
def get_finance(
    ticker: str,
    limit:  int = Query(20, ge=1, le=100, description="최근 N개 분기"),
):
    """
    지정 종목의 분기별 재무 지표 이력과 재무 스코어를 반환합니다.
    최근 `limit`개 분기를 최신순으로 반환합니다.
    """
    try:
        rows, name = svc.get_finance(ticker=ticker, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not rows:
        raise HTTPException(status_code=404, detail=f"종목 {ticker} 재무 데이터를 찾을 수 없습니다.")

    items = [FinanceItem(**r) for r in rows]
    return FinanceResponse(ticker=ticker.zfill(6), name=name, total=len(items), items=items)


@router.get("/{ticker}/latest", response_model=FinanceLatest, summary="종목 최신 분기 재무 요약")
def get_finance_latest(ticker: str):
    """
    지정 종목의 가장 최근 분기 재무 지표 요약을 반환합니다.
    """
    try:
        row = svc.get_finance_latest(ticker=ticker)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not row:
        raise HTTPException(status_code=404, detail=f"종목 {ticker} 재무 데이터를 찾을 수 없습니다.")

    return FinanceLatest(**row)
