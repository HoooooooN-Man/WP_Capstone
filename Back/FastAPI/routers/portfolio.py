"""
routers/portfolio.py
====================
백테스트 결과 + KOSPI 200 자동 포트폴리오 엔드포인트.
"""

from __future__ import annotations

from typing import Literal
from fastapi import APIRouter, HTTPException, Query

from ..services import data as svc
from ..schemas.stocks import BacktestSummaryResponse, BacktestMonthlyResponse
from ..schemas.portfolio import PortfolioItem, PortfolioResponse

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/backtest/summary", response_model=BacktestSummaryResponse, summary="백테스트 성과 요약")
def get_backtest_summary():
    """
    v7 비교표(comparison_summary.csv)와 v8 Walk-Forward 성과(wf_performance_summary.txt)를 반환합니다.
    """
    try:
        data = svc.get_backtest_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not data:
        raise HTTPException(status_code=404, detail="백테스트 결과 파일을 찾을 수 없습니다.")

    return BacktestSummaryResponse(**data)


@router.get("/backtest/monthly", response_model=BacktestMonthlyResponse, summary="월별 수익률 데이터")
def get_backtest_monthly():
    """
    v8 Walk-Forward 월별 수익률(wf_portfolio_monthly_returns.csv)을 반환합니다.
    프론트 차트 연결용 raw 데이터입니다.
    """
    try:
        data = svc.get_backtest_monthly_returns()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return BacktestMonthlyResponse(data=data)


# ── KOSPI 200 자동 포트폴리오 ──────────────────────────────────────────────────

@router.get(
    "/kospi200",
    response_model=PortfolioResponse,
    summary="KOSPI 200 맞춤형 Top 10 포트폴리오",
)
def get_kospi200_portfolio(
    type:          Literal["growth", "stable"] = Query(
        "growth",
        description=(
            "포트폴리오 유형\n"
            "- **growth** (성장형): AI score 상위 10종목\n"
            "- **stable** (안정형): Tier A·B + PBR < 1.5 조건 상위 10종목"
        ),
    ),
    model_version: str = Query("latest", description="모델 버전 (예: v8, latest)"),
):
    """
    KOSPI 200 종목 중 사용자 성향에 맞는 **Top 10 자동 포트폴리오**를 반환합니다.

    | type    | 필터 조건                           | 정렬    |
    |---------|-------------------------------------|---------|
    | growth  | KOSPI 200 전체                       | score↓  |
    | stable  | KOSPI 200 + Tier A·B + PBR < 1.5   | score↓  |

    - **캐시**: 5분 TTL
    """
    try:
        rows = svc.get_kospi200_portfolio(
            portfolio_type=type,
            model_version=model_version,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="포트폴리오 구성 조건에 맞는 종목이 없습니다. stable 타입은 PBR 데이터가 필요합니다.",
        )

    date          = rows[0].get("date", "")
    resolved_ver  = rows[0].get("model_version", model_version)

    items = [
        PortfolioItem(
            rank   = r["rank"],
            ticker = r["ticker"],
            name   = r.get("name"),
            sector = r.get("sector"),
            score  = float(r["score"]),
            tier   = r["tier"],
            pbr    = float(r["pbr"]) if r.get("pbr") is not None else None,
        )
        for r in rows
    ]

    return PortfolioResponse(
        type          = type,
        date          = date,
        model_version = resolved_ver,
        total         = len(items),
        items         = items,
    )
