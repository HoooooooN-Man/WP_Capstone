"""
routers/winners.py
==================
PRD §3.4 — 일자별 승부주 (Top-5) 이력 엔드포인트.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..services.winners_svc import get_winners

router = APIRouter(prefix="/winners", tags=["winners"])


@router.get("", summary="일자별 승부주 Top-5 이력")
def list_winners(
    days_back:     int = Query(21, ge=1, le=120, description="최근 N 거래일"),
    top_k:         int = Query(5,  ge=1, le=20,  description="일자별 상위 K 종목"),
    model_version: str = Query("latest", description="모델 버전"),
):
    """
    `scores` 테이블에서 일자별 상위 `top_k` 종목을 도출해 반환합니다.

    응답: ``{"model_version", "items": [{"date", "winners": [...]}, ...]}`` (날짜 DESC)
    각 winner 에 추천가·현재가·누적수익률·추세(단/중/장) 포함.
    """
    try:
        return get_winners(days_back=days_back, top_k=top_k, model_version=model_version)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"승부주 조회 실패: {e}")
