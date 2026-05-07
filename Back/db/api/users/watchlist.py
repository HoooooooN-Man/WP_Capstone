"""
api/users/watchlist.py
======================
Tier 1.6 (PRD §2.1) — 관심종목 서버 동기화 CRUD.

엔드포인트:
  GET    /users/me/watchlist           → 내 관심종목 목록 (최신 추가순)
  POST   /users/me/watchlist           → 추가 (이미 있으면 idempotent)
  DELETE /users/me/watchlist/{ticker}  → 삭제 (없으면 404)
  POST   /users/me/watchlist/migrate   → localStorage → 서버 일괄 마이그레이션 (1회용)

설계:
  - 인증 필수: session_token 헤더 → users.py 의 _require_current_user 재사용.
  - 응답에 ticker + added_at 만 포함. 점수/티어는 프론트가 :8001 search API
    호출로 enrich (서버 간 결합도 최소화). 캡스톤 범위에서 충분.
  - memo 필드는 UserWatchlist 모델에 컬럼 부재 → 본 라우터에서 미지원.
    추가 시 PRD §2.1 PATCH 엔드포인트로 확장.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User, UserWatchlist
from .users import _require_current_user


router = APIRouter(prefix="/users/me/watchlist", tags=["watchlist"])


# ── 스키마 ────────────────────────────────────────────────────────────────────

class WatchlistEntry(BaseModel):
    """서버 저장된 관심종목 한 건. 점수/티어는 프론트가 별도 enrich."""
    ticker:     str
    added_at:   datetime

    class Config:
        from_attributes = True


class WatchlistAddRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)


class WatchlistMigrateRequest(BaseModel):
    """localStorage 의 관심종목 배열을 한 번에 서버로 이관."""
    tickers: List[str] = Field(default_factory=list, max_items=200)


class WatchlistResponse(BaseModel):
    total: int
    items: List[WatchlistEntry]


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _normalize_ticker(raw: str) -> str:
    """6자리 zero-pad. 영문(예: 미국 ADR)은 대문자로."""
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="티커가 비어있습니다.")
    # 숫자만이면 6자리 zero-pad, 아니면 대문자 유지.
    if s.isdigit():
        return s.zfill(6)
    return s.upper()


# ── 엔드포인트 ───────────────────────────────────────────────────────────────

@router.get("", response_model=WatchlistResponse, summary="내 관심종목 목록")
def list_watchlist(
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """현재 사용자의 관심종목 (최신 추가 우선)."""
    rows = (
        db.query(UserWatchlist)
        .filter(UserWatchlist.user_id == current_user.user_id)
        .order_by(UserWatchlist.created_at.desc())
        .all()
    )
    items = [
        WatchlistEntry(ticker=r.ticker, added_at=r.created_at or datetime.utcnow())
        for r in rows
    ]
    return WatchlistResponse(total=len(items), items=items)


@router.post(
    "",
    response_model=WatchlistEntry,
    status_code=status.HTTP_201_CREATED,
    summary="관심종목 추가",
)
def add_watchlist(
    payload: WatchlistAddRequest,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """
    관심종목 1건 추가. 이미 등록된 티커면 idempotent (기존 row 반환).
    UNIQUE(user_id, ticker) 제약 위반은 서버에서 graceful 처리.
    """
    t = _normalize_ticker(payload.ticker)
    existing = (
        db.query(UserWatchlist)
        .filter(
            UserWatchlist.user_id == current_user.user_id,
            UserWatchlist.ticker == t,
        )
        .first()
    )
    if existing:
        return WatchlistEntry(ticker=existing.ticker, added_at=existing.created_at)

    new_row = UserWatchlist(user_id=current_user.user_id, ticker=t)
    db.add(new_row)
    try:
        db.commit()
    except IntegrityError:
        # 동시 추가 race condition — 다시 조회해서 반환.
        db.rollback()
        existing = (
            db.query(UserWatchlist)
            .filter(
                UserWatchlist.user_id == current_user.user_id,
                UserWatchlist.ticker == t,
            )
            .first()
        )
        if existing:
            return WatchlistEntry(ticker=existing.ticker, added_at=existing.created_at)
        raise HTTPException(status_code=500, detail="추가 중 충돌이 발생했습니다.")

    db.refresh(new_row)
    return WatchlistEntry(ticker=new_row.ticker, added_at=new_row.created_at)


@router.delete(
    "/{ticker}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="관심종목 삭제",
)
def remove_watchlist(
    ticker: str,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """ticker 기준 삭제. 본인 소유 행만 영향."""
    t = _normalize_ticker(ticker)
    deleted = (
        db.query(UserWatchlist)
        .filter(
            UserWatchlist.user_id == current_user.user_id,
            UserWatchlist.ticker == t,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="해당 관심종목이 없습니다.")
    # 204 — body 비움.
    return None


@router.post(
    "/migrate",
    response_model=WatchlistResponse,
    summary="localStorage → 서버 일괄 마이그레이션 (1회용)",
)
def migrate_watchlist(
    payload: WatchlistMigrateRequest,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """
    비로그인 시절 localStorage 에 쌓인 ticker 배열을 서버로 일괄 이관.
    - 이미 있는 티커는 skip (idempotent).
    - 한 번만 부르도록 프론트가 마이그레이션 후 localStorage 비움.
    - 결과로 현재 시점의 전체 watchlist 를 반환.
    """
    inserted = 0
    for raw in payload.tickers:
        try:
            t = _normalize_ticker(raw)
        except HTTPException:
            continue
        exists = (
            db.query(UserWatchlist.id)
            .filter(
                UserWatchlist.user_id == current_user.user_id,
                UserWatchlist.ticker == t,
            )
            .first()
        )
        if exists:
            continue
        db.add(UserWatchlist(user_id=current_user.user_id, ticker=t))
        inserted += 1
    if inserted:
        try:
            db.commit()
        except IntegrityError:
            # 동시 마이그레이션 충돌 — 부분 성공도 OK.
            db.rollback()

    rows = (
        db.query(UserWatchlist)
        .filter(UserWatchlist.user_id == current_user.user_id)
        .order_by(UserWatchlist.created_at.desc())
        .all()
    )
    items = [
        WatchlistEntry(ticker=r.ticker, added_at=r.created_at or datetime.utcnow())
        for r in rows
    ]
    return WatchlistResponse(total=len(items), items=items)
