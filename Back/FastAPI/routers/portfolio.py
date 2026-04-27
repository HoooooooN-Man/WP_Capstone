"""
routers/portfolio.py
====================
백테스트 결과 관련 엔드포인트.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..services import data as svc
from ..schemas.stocks import BacktestSummaryResponse, BacktestMonthlyResponse, BacktestRequest, CustomBacktestResponse

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
