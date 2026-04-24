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
    전체 종목 대비 **Tier A 비율**로 현재 시장 국면을 반환합니다.

    | Tier A 비율 | status  | weather | 설명                         |
    |------------|---------|---------|------------------------------|
    | 10% 이상   | greed   | 맑음    | 강한 상승 모멘텀              |
    | 5~10% 미만 | neutral | 흐림    | 방향성 탐색 구간              |
    | 5% 미만    | fear    | 비      | 변동성 확대, 현금 비중 권장    |

    - **캐시**: 5분 TTL (Redis 없으면 DuckDB 직접 조회)
    """
    try:
        result = svc.get_market_regime(model_version=model_version)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return MarketRegimeResponse(**result)
