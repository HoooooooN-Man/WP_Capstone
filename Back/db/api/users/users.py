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

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import User, UserWatchlist, Notification
from api.auth.auth import rd  # Redis 연결 공유

router = APIRouter(prefix="/users", tags=["users"])


# ── 인증 헬퍼 ─────────────────────────────────────────────────────────────────

def _get_current_user_or_none(
    session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """세션 토큰이 있으면 User 객체 반환, 없으면 None."""
    if not session_token:
        return None
    email = rd.get(f"session:{session_token}")
    if not email:
        return None
    return db.query(User).filter(User.email == email).first()


def _require_current_user(
    session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """세션 토큰이 없거나 만료됐으면 401."""
    if not session_token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    email = rd.get(f"session:{session_token}")
    if not email:
        raise HTTPException(status_code=401, detail="세션이 만료됐습니다. 다시 로그인해주세요.")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user


# ── 스키마 ────────────────────────────────────────────────────────────────────

class NotificationItem(BaseModel):
    id:              int
    ticker:          Optional[str] = None
    title:           Optional[str] = None
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
                body=n.sentiment_label,
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
