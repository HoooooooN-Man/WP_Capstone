"""
routers/stocks.py
=================
종목 추천·이력·섹터 관련 엔드포인트.
모두 /api/v1/ 접두사는 main.py에서 prefix로 부착.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from ..services import data as svc
from ..schemas.stocks import (
    StockScore,
    StockScoreList,
    StockHistory,
    StockHistoryItem,
    SectorSummaryList,
    SectorSummaryItem,
    VersionsResponse,
    DatesResponse,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


# ── 버전·날짜 메타 ─────────────────────────────────────────────────────────────

@router.get("/versions", response_model=VersionsResponse, summary="사용 가능한 model_version 목록")
def list_versions():
    versions = svc.get_available_versions()
    return VersionsResponse(
        versions=versions,
        latest=versions[-1] if versions else None,
    )


@router.get("/dates", response_model=DatesResponse, summary="사용 가능한 날짜 목록")
def list_dates(
    model_version: str = Query("latest", description="모델 버전 (예: v7, latest)"),
):
    try:
        dates = svc.get_available_dates(model_version)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return DatesResponse(
        model_version=model_version,
        dates=dates,
        latest=dates[-1] if dates else None,
    )


# ── 추천 목록 ──────────────────────────────────────────────────────────────────

@router.get("/recommendations", response_model=StockScoreList, summary="종목 추천 목록")
def get_recommendations(
    date:          Optional[str]   = Query(None,      description="조회 날짜 YYYY-MM-DD (생략 시 최신)"),
    model_version: str             = Query("latest",  description="모델 버전 (예: v7, latest)"),
    sector:        Optional[str]   = Query(None,      description="섹터 필터 (예: IT, 금융)"),
    top_k:         int             = Query(20,        ge=0, le=500, description="상위 N개 (0=전체)"),
    min_score:     float           = Query(0.0,       ge=0, le=100, description="최소 점수 필터"),
):
    """
    날짜·섹터·점수 필터로 추천 종목을 내림차순으로 반환합니다.

    - **model_version=latest** → 가장 최근 적재된 버전 자동 선택
    - **top_k=0** → 전체 반환
    - **min_score=60** → B티어 이상(60점 이상)만 반환
    """
    try:
        rows = svc.get_recommendations(
            date=date,
            model_version=model_version,
            sector=sector,
            top_k=top_k,
            min_score=min_score,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not rows:
        raise HTTPException(status_code=404, detail="해당 날짜·조건에 맞는 데이터가 없습니다.")

    items = [StockScore(**r) for r in rows]
    resolved_date = items[0].date if items else (date or "")
    resolved_ver  = items[0].model_version if items else model_version

    return StockScoreList(
        date=resolved_date,
        model_version=resolved_ver,
        total=len(items),
        items=items,
    )


# ── 종목 상세 이력 ─────────────────────────────────────────────────────────────

@router.get("/{ticker}/history", response_model=StockHistory, summary="종목 스코어 이력")
def get_stock_history(
    ticker:        str,
    model_version: str           = Query("latest", description="모델 버전"),
    start_date:    Optional[str] = Query(None,     description="시작일 YYYY-MM-DD"),
    end_date:      Optional[str] = Query(None,     description="종료일 YYYY-MM-DD"),
):
    """특정 종목의 날짜별 추천 점수 이력을 반환합니다 (차트·분석용)."""
    try:
        rows = svc.get_stock_history(
            ticker=ticker,
            model_version=model_version,
            start_date=start_date,
            end_date=end_date,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not rows:
        raise HTTPException(status_code=404, detail=f"종목 {ticker} 데이터를 찾을 수 없습니다.")

    items = [StockHistoryItem(**r) for r in rows]
    resolved_ver = items[0].model_version if items else model_version

    return StockHistory(
        ticker=ticker.zfill(6),
        model_version=resolved_ver,
        total=len(items),
        items=items,
    )


# ── 섹터 요약 ──────────────────────────────────────────────────────────────────

@router.get("/sectors/summary", response_model=SectorSummaryList, summary="섹터별 평균 점수 요약")
def get_sector_summary(
    date:          Optional[str] = Query(None,     description="조회 날짜 (생략 시 최신)"),
    model_version: str           = Query("latest", description="모델 버전"),
):
    """섹터별 평균·최대·최소 점수 및 A티어 종목 수를 반환합니다."""
    try:
        rows = svc.get_sector_summary(date=date, model_version=model_version)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not rows:
        raise HTTPException(status_code=404, detail="해당 조건의 섹터 데이터가 없습니다.")

    items = [SectorSummaryItem(**r) for r in rows]
    resolved_date = items[0].date if items else (date or "")
    resolved_ver  = items[0].model_version if items else model_version

    return SectorSummaryList(
        date=resolved_date,
        model_version=resolved_ver,
        total=len(items),
        items=items,
    )
