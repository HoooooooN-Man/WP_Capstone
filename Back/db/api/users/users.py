"""
api/users/users.py
==================
사용자 관련 엔드포인트:
  - GET  /users/notifications          현재 로그인 사용자 알림 목록
  - POST /users/notifications/read-all 모든 알림 읽음 처리
  - GET  /users/{nickname}/public      공개 프로필 조회
"""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Header, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

import redis as _redis  # 예외 타입 catch 용

from db.database import get_db
from db.models import User, UserWatchlist, Notification
from api.auth.auth import (
    rd, get_current_user as _get_current_email,
)  # Redis + 통합 토큰 해석 (cookie + header + fingerprint)

router = APIRouter(prefix="/users", tags=["users"])


# ── 인증 헬퍼 ─────────────────────────────────────────────────────────────────
# H#27 + IP/UA fingerprint: 모든 토큰 해석은 auth.get_current_user 로 위임.
# 호출자는 헤더(session-token) 또는 쿠키(wp_session) 중 어느 쪽이든 그대로 전달.

def _get_current_user_or_none(
    request: Request,
    session_token: Optional[str] = Header(None),
    wp_session: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """토큰 있으면 User 반환, 없거나 만료/위변조면 None.

    fingerprint 불일치도 None 으로 처리 (Optional 시그니처 — 비로그인 동작).
    """
    if not session_token and not wp_session:
        return None
    try:
        email = _get_current_email(request, session_token, wp_session)
    except HTTPException:
        return None
    return db.query(User).filter(User.email == email).first()


def _require_current_user(
    request: Request,
    session_token: Optional[str] = Header(None),
    wp_session: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
) -> User:
    """세션이 없거나 만료/fingerprint 불일치면 401, Redis 장애면 503."""
    email = _get_current_email(request, session_token, wp_session)  # 내부에서 401/503 raise
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user


# ── 스키마 ────────────────────────────────────────────────────────────────────

class NotificationItem(BaseModel):
    id:              int
    ticker:          Optional[str] = None
    title:           Optional[str] = None
    # body 는 현재 DB 모델에 존재하지 않아 항상 None.
    # 이전 구현은 sentiment_label 을 body 에 그대로 복사해 알림 본문이
    # "positive"/"neutral" 만 표시되는 placeholder 버그가 있었다.
    body:            Optional[str] = None
    sentiment_label: Optional[str] = None
    is_read:         bool
    created_at:      datetime

    class Config:
        from_attributes = True


class NotificationsResponse(BaseModel):
    unread_count: int
    total:        int
    items:        List[NotificationItem]


class WatchlistItem(BaseModel):
    ticker: str
    name:   Optional[str] = None
    tier:   Optional[str] = None
    score:  Optional[float] = None


class PublicPostItem(BaseModel):
    id:         int
    ticker:     Optional[str] = None
    title:      Optional[str] = None
    created_at: Optional[datetime] = None
    likes:      int = 0


class PublicProfileResponse(BaseModel):
    nickname:        str
    bio:             Optional[str] = None
    joined_at:       Optional[datetime] = None
    post_count:      int = 0
    follower_count:  int = 0
    following_count: int = 0
    is_following:    bool = False
    public_watchlist: List[WatchlistItem] = []
    recent_posts:    List[PublicPostItem] = []


# ── 내 프로필 ─────────────────────────────────────────────────────────────────

class MeResponse(BaseModel):
    user_id:     int
    email:       str
    nickname:    str
    cohort:      Optional[str] = None
    is_verified: bool = False
    # DB 컬럼이 server_default=func.now() 라 row 가 존재하는 한 항상 set.
    # 이전 Optional[str] 은 불필요해 FE 가 매번 null 체크를 하게 만들었다.
    created_at:  str

    class Config:
        from_attributes = True


@router.get("/me", response_model=MeResponse, summary="내 프로필 조회")
def get_me(current_user: User = Depends(_require_current_user)):
    """현재 로그인 사용자의 기본 프로필(이메일·닉네임·코호트·가입일)."""
    return MeResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        nickname=current_user.nickname,
        cohort=current_user.cohort,
        is_verified=bool(current_user.is_verified),
        # server_default 가 있어 NULL 인 경우는 사실상 없지만 legacy row 방어용 "".
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
    )


# ── 알림 엔드포인트 ───────────────────────────────────────────────────────────

@router.get("/notifications", response_model=NotificationsResponse, summary="내 알림 목록")
def get_notifications(
    unread: bool = Query(False, description="읽지 않은 알림만"),
    limit:  int  = Query(20, ge=1, le=100),
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """현재 로그인된 사용자의 알림 목록을 반환합니다."""
    query = db.query(Notification).filter(Notification.user_id == current_user.user_id)
    if unread:
        query = query.filter(Notification.is_read == False)  # noqa: E712
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    items = query.all()

    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.is_read == False,  # noqa: E712
    ).count()

    return NotificationsResponse(
        unread_count=unread_count,
        total=len(items),
        items=[
            NotificationItem(
                id=n.id,
                ticker=n.ticker,
                title=n.title,
                # body 는 DB 컬럼 부재 — None 고정. FE 는 sentiment_label 또는 title 사용.
                body=None,
                sentiment_label=n.sentiment_label,
                is_read=n.is_read,
                created_at=n.created_at,
            )
            for n in items
        ],
    )


@router.post("/notifications/read-all", summary="모든 알림 읽음 처리")
def mark_all_read(
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """현재 사용자의 읽지 않은 알림을 모두 읽음으로 처리합니다."""
    db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.is_read == False,  # noqa: E712
    ).update({"is_read": True})
    db.commit()
    return {"message": "모든 알림을 읽음 처리했습니다."}


# ── 공개 프로필 엔드포인트 ────────────────────────────────────────────────────

@router.get("/{nickname}/public", response_model=PublicProfileResponse, summary="공개 프로필 조회")
def get_public_profile(
    nickname: str,
    current_user: Optional[User] = Depends(_get_current_user_or_none),
    db: Session = Depends(get_db),
):
    """
    닉네임으로 사용자의 공개 프로필을 조회합니다.
    로그인한 경우 팔로우 여부(is_following)도 포함합니다.
    """
    user = db.query(User).filter(User.nickname == nickname).first()
    if not user:
        raise HTTPException(status_code=404, detail="존재하지 않는 사용자입니다.")

    # 공개 관심종목
    watchlist_items = db.query(UserWatchlist).filter(
        UserWatchlist.user_id == user.user_id
    ).limit(10).all()

    public_watchlist = [
        WatchlistItem(ticker=w.ticker)
        for w in watchlist_items
    ]

    # 최근 게시글 (board.py 의 Post 모델과 연동이 필요하지만,
    # 현재 SQLite board DB와 PostgreSQL user DB가 분리돼 있으므로
    # 이 버전에서는 빈 목록을 반환합니다.)
    recent_posts: List[PublicPostItem] = []

    # 팔로우 여부 (follower 테이블이 없으므로 항상 False)
    is_following = False

    return PublicProfileResponse(
        nickname=user.nickname,
        bio=None,
        joined_at=user.created_at,
        post_count=0,
        follower_count=0,
        following_count=0,
        is_following=is_following,
        public_watchlist=public_watchlist,
        recent_posts=recent_posts,
    )
