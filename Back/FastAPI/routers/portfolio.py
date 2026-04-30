"""
routers/portfolio.py
====================
백테스트 결과 관련 엔드포인트.
"""

from __future__ import annotations

from typing import Literal
from fastapi import APIRouter, HTTPException, Query

from ..services import data as svc
from ..schemas.stocks import BacktestSummaryResponse, BacktestMonthlyResponse, BacktestRequest, CustomBacktestResponse
from ..schemas.portfolio import PortfolioResponse

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


@router.post("/backtest", response_model=CustomBacktestResponse, summary="커스텀 백테스트 시뮬레이션")
def run_custom_backtest(req: BacktestRequest):
    """
    사용자 정의 조건(최소 점수, 종목 수, 리밸런싱 주기, 기간)으로
    ML 전략 vs KOSPI 벤치마크 수익률을 시뮬레이션합니다.
    """
    try:
        data = svc.run_custom_backtest(
            min_score=req.min_score,
            top_k=req.top_k,
            rebalance=req.rebalance,
            start_date=req.start_date,
            end_date=req.end_date,
            model_version=req.model_version,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"백테스트 실패: {str(e)}")

    return CustomBacktestResponse(**data)


@router.get(
    "/kospi200",
    response_model=PortfolioResponse,
    summary="KOSPI 200 맞춤형 자동 포트폴리오 (Top 10)",
)
def get_kospi200_portfolio(
    type: Literal["growth", "stable"] = Query("growth", description="growth=공격형, stable=안정형(PBR<1.5)"),
    model_version: str = Query("latest", description="모델 버전 (예: v8, latest)"),
):
    """
    사용자 성향별 **KOSPI 200 Top 10 자동 포트폴리오**를 제공합니다.

    | type   | 선정 기준                                                  |
    |--------|------------------------------------------------------------|
    | growth | 단순 AI score 상위 10                                       |
    | stable | Tier A·B + 최신 분기 PBR < 1.5 + score 상위 10              |

    - **캐시**: 5분 TTL (Redis 없으면 DuckDB 직접 조회)
    """
    try:
        result = svc.get_kospi200_portfolio(
            portfolio_type=type, model_version=model_version
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"포트폴리오 조회 실패: {str(e)}")

    return PortfolioResponse(**result)
