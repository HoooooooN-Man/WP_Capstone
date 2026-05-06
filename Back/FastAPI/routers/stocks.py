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
    StockSearchResult,
    StockSearchList,
    StockPrice,
    RisingStockList,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


# ── 버전·날짜 메타 ─────────────────────────────────────────────────────────────

@router.get("/versions", response_model=VersionsResponse, summary="사용 가능한 model_version 목록")
def list_versions():
    versions = svc.get_available_versions()  # inserted_at DESC 순 (v9 먼저)
    return VersionsResponse(
        versions=versions,
        latest=versions[0] if versions else None,
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
    model_version: str             = Query("latest",  description="모델 버전 (예: v9, latest)"),
    sector:        Optional[str]   = Query(None,      description="섹터 필터 (예: IT, 금융)"),
    top_k:         int             = Query(20,        ge=0, le=500, description="상위 N개 (0=전체)"),
    min_score:     float           = Query(0.0,       ge=0, le=100, description="최소 점수 필터"),
    strategy:      str             = Query("base",    description="선별 전략: base(기본) | s3(v9 S3: prob Top-150 + 레짐 신호)"),
):
    """
    날짜·섹터·점수 필터로 추천 종목을 내림차순으로 반환합니다.

    - **model_version=latest** → 가장 최근 적재된 버전 자동 선택
    - **top_k=0** → 전체 반환
    - **min_score=60** → B티어 이상(60점 이상)만 반환
    - **strategy=s3** → v9 S3 전략: prob 상위 150 + KOSPI 레짐 신호 포함
      - `regime` 필드: 1=상승, 0=하락(방어)
      - `position_scale` 필드: 1.0 또는 0.5 (하락장 포지션 50% 축소 권고)
    """
    if strategy not in ("base", "s3"):
        strategy = "base"
    try:
        rows = svc.get_recommendations(
            date=date,
            model_version=model_version,
            sector=sector,
            top_k=top_k,
            min_score=min_score,
            strategy=strategy,
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


# ── 종목 검색 ──────────────────────────────────────────────────────────────────

@router.get("/search", response_model=StockSearchList, summary="종목 검색 (티커·회사명)")
def search_stocks(
    q:             str           = Query(..., min_length=1, description="검색 키워드 (티커 또는 회사명)"),
    model_version: str           = Query("latest", description="모델 버전"),
    limit:         int           = Query(20, ge=1, le=100, description="최대 결과 수"),
):
    """
    티커 코드 또는 회사명 키워드로 종목을 검색합니다.
    가장 최신 날짜 기준의 ML 점수·티어를 함께 반환합니다.
    """
    try:
        rows = svc.search_stocks(q=q, model_version=model_version, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    items = [StockSearchResult(**r) for r in rows]
    return StockSearchList(query=q, total=len(items), items=items)


# ── 종목 현재가 ────────────────────────────────────────────────────────────────

@router.get("/{ticker}/price", response_model=StockPrice, summary="종목 최신 현재가")
def get_stock_price(ticker: str):
    """prices 테이블 기준 가장 최신 종가(현재가)를 반환합니다."""
    try:
        data = svc.get_stock_price(ticker)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if data is None:
        raise HTTPException(status_code=404, detail=f"종목 {ticker} 의 가격 데이터가 없습니다.")

    return StockPrice(**data)


# ── 급상승 종목 ────────────────────────────────────────────────────────────────

@router.get("/rising", response_model=RisingStockList, summary="전일 대비 급상승 종목")
def get_rising_stocks(
    model_version: str = Query("latest", description="모델 버전"),
    limit:         int = Query(20, ge=1, le=100, description="반환 종목 수"),
):
    """최신 날짜 기준 전 거래일 대비 ML 점수 변화량(score_change) 상위 종목을 반환합니다."""
    try:
        data = svc.get_rising_stocks(model_version=model_version, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    items = data.get("items", [])
    return RisingStockList(
        total=data.get("total", len(items)),
        date=data.get("date", ""),
        model_version=data.get("model_version", model_version),
        items=items,
    )
