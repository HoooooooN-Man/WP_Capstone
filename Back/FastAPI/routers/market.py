"""
routers/market.py
=================
마켓 레이더(시장 기상도) 엔드포인트.

Tier A 종목 비율로 현재 시장 국면을 판단해 대시보드에 제공한다.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..services import data as svc
from ..schemas.portfolio import MarketRegimeResponse

router = APIRouter(prefix="/market", tags=["market"])


@router.get(
    "/regime",
    response_model=MarketRegimeResponse,
    summary="마켓 레이더 — 시장 국면(기상도) 조회",
)
def get_market_regime(
    model_version: str = Query("latest", description="모델 버전 (예: v8, latest)"),
):
    """
    KOSPI 일/주간 변화율 + 모델 평균 prob_ensemble 로 0~100 마켓스코어 산출 (B21).

    | score   | status     | status_ko | weather | 설명                       |
    |---------|------------|-----------|---------|----------------------------|
    | 0-19    | panic      | 패닉      | 비      | 시장 공포·현금 비중 확대   |
    | 20-39   | pessimism  | 비관      | 흐림    | 비관 분위기·선별적 매수    |
    | 40-59   | neutral    | 중립      | 흐림    | 방향성 탐색                |
    | 60-79   | optimism   | 낙관      | 맑음    | 상승 모멘텀                |
    | 80-100  | greed      | 과욕      | 맑음    | 과열 위험·분할 차익실현    |

    공식 (B21): score = 50 + daily×800 + weekly×300 + (avg_prob−0.5)×100, clamp 0~100.
    이전 `tier_a_ratio × 5` 는 ML 백분위 구조상 ratio≈20% 고정이라 무효였음.

    - **캐시**: 5분 TTL (Redis 없으면 DuckDB 직접 조회)
    """
    try:
        result = svc.get_market_regime(model_version=model_version)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return MarketRegimeResponse(**result)
