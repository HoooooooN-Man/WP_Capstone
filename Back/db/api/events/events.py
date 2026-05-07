"""
api/events/events.py
====================
W1B Step 2 — events_v1 적재 라우터.

엔드포인트:
  POST  /events/impressions       배치 적재 (items 배열, 단건도 1-element)
  POST  /events/clicks            클릭 단건 적재
  PATCH /events/clicks/{click_id} 이탈 시 dwell_ms / followup_action 갱신
  GET   /events/health            events_v1_meta 한 줄 (디버그)

설계 (W1B_명세 §2):
  - 인증: `_get_current_user_or_none` — 비로그인은 session_id 필수, 로그인은 user_id 자동.
  - PATCH 권한: 같은 user_id 또는 같은 session_id 가 만든 click 만 수정 허용 → 그 외 403.
  - CLAUDE.md §컴플라이언스: 응답에 `is_advice: false`, "추천/투자자문/매수" 단어 없음.
  - 적재 실패 graceful: 404·400·403 만 명시 사유, 5xx 는 글로벌 핸들러 (인증 서버 기본).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import (
    EventsV1Meta,
    RecommendationClick,
    RecommendationImpression,
    User,
)
from ..users.users import _get_current_user_or_none


router = APIRouter(prefix="/events", tags=["events"])


# ── Pydantic 스키마 ─────────────────────────────────────────────────────────

class ShownTickerEntry(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    rank:   int = Field(..., ge=1)
    score:  Optional[float] = None
    tier:   Optional[str]   = None


class ImpressionIn(BaseModel):
    """단건 impression payload. user_id 는 서버가 세션에서 결정."""
    session_id:        Optional[str]                = Field(None, max_length=64)
    cohort:            Optional[str]                = Field(None, max_length=20)
    shown_tickers:     List[ShownTickerEntry]       = Field(..., min_length=1, max_length=200)
    model_version:     str                          = Field(..., min_length=1, max_length=20)
    embedding_version: Optional[str]                = Field(None, max_length=20)
    page_context:      Optional[str]                = Field(None, max_length=50)


class ImpressionsBatchRequest(BaseModel):
    items: List[ImpressionIn] = Field(..., min_length=1, max_length=100)


class ImpressionRecorded(BaseModel):
    impression_id: UUID
    shown_at:      datetime


class ImpressionsBatchResponse(BaseModel):
    accepted: int
    items:    List[ImpressionRecorded]
    is_advice: bool = False    # CLAUDE.md §컴플라이언스


class ClickIn(BaseModel):
    impression_id:   UUID
    ticker:          str = Field(..., min_length=1, max_length=10)
    rank_clicked:    int = Field(..., ge=1)
    session_id:      Optional[str] = Field(None, max_length=64)


class ClickRecorded(BaseModel):
    click_id:        UUID
    impression_id:   UUID
    clicked_at:      datetime
    is_advice:       bool = False


class ClickPatch(BaseModel):
    dwell_ms:        Optional[int] = Field(None, ge=0)
    followup_action: Optional[str] = Field(None, max_length=30)
    session_id:      Optional[str] = Field(None, max_length=64)

    @field_validator("dwell_ms", "followup_action")
    @classmethod
    def _at_least_one(cls, v):
        return v


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _resolve_identity(
    body_session_id: Optional[str],
    current_user: Optional[User],
) -> tuple[Optional[int], Optional[str]]:
    """
    인증 정책: 로그인 시 user_id 자동 채움. 비로그인 시 session_id 필수.
    둘 다 없으면 400.
    """
    user_id = current_user.user_id if current_user else None
    session_id = body_session_id
    if user_id is None and not session_id:
        raise HTTPException(
            status_code=400,
            detail="user_id 또는 session_id 중 하나는 필수입니다 (비로그인 시 session_id).",
        )
    return user_id, session_id


# ── 엔드포인트 ───────────────────────────────────────────────────────────────

@router.post(
    "/impressions",
    response_model=ImpressionsBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="추천 노출 배치 적재",
)
def record_impressions(
    payload: ImpressionsBatchRequest,
    current_user: Optional[User] = Depends(_get_current_user_or_none),
    db: Session = Depends(get_db),
):
    user_id_default = current_user.user_id if current_user else None
    accepted: list[RecommendationImpression] = []

    for item in payload.items:
        # 항목별 session_id (배치 안에서 device 가 달라질 수도 있음 — 일반적으론 동일).
        sid = item.session_id
        if user_id_default is None and not sid:
            raise HTTPException(
                status_code=400,
                detail="비로그인 적재는 모든 항목에 session_id 필요.",
            )
        row = RecommendationImpression(
            user_id=user_id_default,
            session_id=sid,
            cohort=item.cohort,
            shown_tickers=[t.model_dump(exclude_none=True) for t in item.shown_tickers],
            model_version=item.model_version,
            embedding_version=item.embedding_version,
            page_context=item.page_context,
        )
        db.add(row)
        accepted.append(row)

    db.commit()
    for r in accepted:
        db.refresh(r)

    return ImpressionsBatchResponse(
        accepted=len(accepted),
        items=[
            ImpressionRecorded(impression_id=r.impression_id, shown_at=r.shown_at)
            for r in accepted
        ],
    )


@router.post(
    "/clicks",
    response_model=ClickRecorded,
    status_code=status.HTTP_201_CREATED,
    summary="추천 클릭 단건 적재",
)
def record_click(
    payload: ClickIn,
    current_user: Optional[User] = Depends(_get_current_user_or_none),
    db: Session = Depends(get_db),
):
    _resolve_identity(payload.session_id, current_user)

    # impression_id 존재 검증.
    imp = db.query(RecommendationImpression).filter_by(
        impression_id=payload.impression_id
    ).first()
    if imp is None:
        raise HTTPException(status_code=404, detail="impression_id 가 존재하지 않습니다.")

    # 권한: 동일 user 또는 동일 session 의 impression 에만 click 적재.
    if not _is_same_origin(imp, current_user, payload.session_id):
        raise HTTPException(
            status_code=403, detail="해당 노출에 대한 클릭 적재 권한이 없습니다.",
        )

    click = RecommendationClick(
        impression_id=payload.impression_id,
        ticker=payload.ticker,
        rank_clicked=payload.rank_clicked,
    )
    db.add(click)
    db.commit()
    db.refresh(click)

    return ClickRecorded(
        click_id=click.click_id,
        impression_id=click.impression_id,
        clicked_at=click.clicked_at,
    )


@router.patch(
    "/clicks/{click_id}",
    response_model=ClickRecorded,
    summary="이탈 시 dwell_ms / followup_action 갱신",
)
def patch_click(
    click_id: UUID,
    payload: ClickPatch,
    current_user: Optional[User] = Depends(_get_current_user_or_none),
    db: Session = Depends(get_db),
):
    if payload.dwell_ms is None and payload.followup_action is None:
        raise HTTPException(
            status_code=400,
            detail="dwell_ms 또는 followup_action 중 하나는 필요합니다.",
        )

    click = db.query(RecommendationClick).filter_by(click_id=click_id).first()
    if click is None:
        raise HTTPException(status_code=404, detail="click_id 가 존재하지 않습니다.")

    imp = click.impression
    if imp is None:
        # 거의 발생하지 않음 (CASCADE) — 방어.
        raise HTTPException(status_code=404, detail="연결된 impression 이 없습니다.")

    if not _is_same_origin(imp, current_user, payload.session_id):
        raise HTTPException(
            status_code=403, detail="해당 click 수정 권한이 없습니다.",
        )

    if payload.dwell_ms is not None:
        click.dwell_ms = payload.dwell_ms
    if payload.followup_action is not None:
        click.followup_action = payload.followup_action

    db.commit()
    db.refresh(click)

    return ClickRecorded(
        click_id=click.click_id,
        impression_id=click.impression_id,
        clicked_at=click.clicked_at,
    )


@router.get("/health", summary="events_v1 스키마 메타 (디버그)")
def events_health(db: Session = Depends(get_db)):
    meta = db.query(EventsV1Meta).filter_by(schema_version="v1").first()
    if meta is None:
        return {
            "schema_version": None,
            "applied_at":     None,
            "is_advice":      False,
            "message":        "events_v1 schema not applied",
        }
    return {
        "schema_version": meta.schema_version,
        "applied_at":     meta.applied_at.isoformat() if meta.applied_at else None,
        "is_advice":      False,
    }


# ── 권한 확인 ───────────────────────────────────────────────────────────────

def _is_same_origin(
    imp: RecommendationImpression,
    current_user: Optional[User],
    body_session_id: Optional[str],
) -> bool:
    """impression 을 만든 주체 == 현재 요청 주체 인가?"""
    # 로그인 사용자: user_id 일치.
    if current_user and imp.user_id is not None:
        return imp.user_id == current_user.user_id
    # 비로그인 또는 anonymous-impression 로그인: session_id 일치.
    if imp.session_id is not None and body_session_id is not None:
        return imp.session_id == body_session_id
    # 둘 다 user_id NULL 이고 양쪽 session_id 도 부재 — 서버 운영자 적재 등 예외.
    return False
