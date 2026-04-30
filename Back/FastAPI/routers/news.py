"""
routers/news.py
================
뉴스 피드 + 단건 상세 (FinBERT 감성 분석).

dbapi.js의 baseURL이 `http://localhost:8000` (no /api/v1 prefix) 이므로
이 라우터는 `prefix=""` 로 등록되어 `/news/feed` 로 노출된다.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from ..services import data as svc

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/feed", summary="뉴스 피드 (감성 라벨 + origin_url 포함)")
def list_news_feed(
    limit:     int = Query(20, ge=1, le=100),
    offset:    int = Query(0,  ge=0),
    sentiment: Optional[str] = Query(None, description="positive | neutral | negative"),
    ticker:    Optional[str] = Query(None, description="종목 코드/회사명 LIKE 매칭"),
):
    """
    `news_normalized` 테이블에서 최신순으로 뉴스 피드를 반환합니다.

    응답 형식 (NewsView.vue 호환):
        ``{"total": int, "items": [...]}``

    - 각 item에 `url`(origin_url)이 포함되므로 모달의 **기사 원문 읽기** 버튼 동작.
    - `sentiment_label`, `pos_prob`, `neg_prob`, `neu_prob` 모두 노출.
    """
    try:
        return svc.get_news_feed(
            limit=limit, offset=offset, sentiment=sentiment, ticker=ticker,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"뉴스 조회 실패: {e}")


@router.get("/detail/{news_id}", summary="뉴스 단건 상세")
def get_news_detail(news_id: str):
    item = svc.get_news_detail(news_id)
    if item is None:
        raise HTTPException(status_code=404, detail="뉴스 없음")
    return item
