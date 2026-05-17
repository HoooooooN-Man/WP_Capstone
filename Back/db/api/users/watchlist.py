"""
api/users/watchlist.py
======================
Tier 1.6 (PRD §2.1) — 관심종목 서버 동기화 CRUD.
P0-3 (PRD §8.1) — 그룹 분류 (보유 / 배당 / 관심 등) 다중 watchlist 지원.

엔드포인트:
  GET    /users/me/watchlist                 → 내 관심종목 목록 (group 필터 옵션)
  POST   /users/me/watchlist                 → 추가 (group_name 지정 가능)
  DELETE /users/me/watchlist/{ticker}        → 삭제 (group 필터 옵션)
  POST   /users/me/watchlist/migrate         → localStorage 일괄 마이그레이션
  GET    /users/me/watchlist/groups          → 사용자의 그룹 목록 + 각 종목 수
  PATCH  /users/me/watchlist/{ticker}/group  → 종목의 그룹 변경

설계:
  - group_name = 'default' 가 분류 미선택 기본값.
  - UNIQUE(user_id, ticker, group_name) — 동일 ticker 를 여러 그룹에 등록 가능.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User, UserWatchlist
from .users import _require_current_user


router = APIRouter(prefix="/users/me/watchlist", tags=["watchlist"])


DEFAULT_GROUP = "default"
MAX_GROUP_NAME_LEN = 50


# ── 스키마 ────────────────────────────────────────────────────────────────────

class WatchlistEntry(BaseModel):
    ticker:     str
    group_name: str = DEFAULT_GROUP
    added_at:   datetime

    class Config:
        from_attributes = True


class WatchlistAddRequest(BaseModel):
    ticker:     str = Field(..., min_length=1, max_length=20)
    group_name: str = Field(default=DEFAULT_GROUP, max_length=MAX_GROUP_NAME_LEN)


class WatchlistMigrateRequest(BaseModel):
    tickers:    List[str] = Field(default_factory=list, max_items=200)
    group_name: str = Field(default=DEFAULT_GROUP, max_length=MAX_GROUP_NAME_LEN)


class WatchlistResponse(BaseModel):
    total: int
    items: List[WatchlistEntry]


class GroupInfo(BaseModel):
    group_name: str
    count:      int


class GroupsResponse(BaseModel):
    total_groups: int
    groups:       List[GroupInfo]


class GroupChangeRequest(BaseModel):
    group_name: str = Field(..., max_length=MAX_GROUP_NAME_LEN)


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _normalize_ticker(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="티커가 비어있습니다.")
    if s.isdigit():
        return s.zfill(6)
    return s.upper()


def _normalize_group(raw: Optional[str]) -> str:
    """그룹명 정규화.

    이전엔 `s[:50]` 으로 silent truncate → 50자 prefix 가 같은 두 그룹이 충돌.
    이제 한계 초과면 400 으로 명확히 거절한다.
    """
    s = (raw or "").strip()
    if not s:
        return DEFAULT_GROUP
    if len(s) > MAX_GROUP_NAME_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"그룹명은 최대 {MAX_GROUP_NAME_LEN}자까지 입력 가능합니다.",
        )
    return s


# ── 엔드포인트 ───────────────────────────────────────────────────────────────

@router.get("", response_model=WatchlistResponse, summary="내 관심종목 목록")
def list_watchlist(
    group_name: Optional[str] = Query(None, description="그룹 필터. 미지정 시 전체."),
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """현재 사용자의 관심종목 (최신 추가 우선). group_name 지정 시 해당 그룹만."""
    q = db.query(UserWatchlist).filter(UserWatchlist.user_id == current_user.user_id)
    if group_name is not None:
        q = q.filter(UserWatchlist.group_name == _normalize_group(group_name))
    rows = q.order_by(UserWatchlist.created_at.desc()).all()
    items = [
        WatchlistEntry(
            ticker=r.ticker,
            group_name=r.group_name or DEFAULT_GROUP,
            added_at=r.created_at or datetime.utcnow(),
        )
        for r in rows
    ]
    return WatchlistResponse(total=len(items), items=items)


@router.get("/groups", response_model=GroupsResponse, summary="내 watchlist 그룹 목록 + 각 종목 수")
def list_groups(
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """사용자가 만든 그룹 + 그룹별 종목 수를 반환 (P0-3)."""
    rows = (
        db.query(UserWatchlist.group_name, func.count(UserWatchlist.id))
        .filter(UserWatchlist.user_id == current_user.user_id)
        .group_by(UserWatchlist.group_name)
        .order_by(UserWatchlist.group_name)
        .all()
    )
    groups = [GroupInfo(group_name=(g or DEFAULT_GROUP), count=int(c)) for g, c in rows]
    return GroupsResponse(total_groups=len(groups), groups=groups)


@router.post(
    "",
    response_model=WatchlistEntry,
    status_code=status.HTTP_201_CREATED,
    summary="관심종목 추가 (group_name 지정 가능)",
)
def add_watchlist(
    payload: WatchlistAddRequest,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    t = _normalize_ticker(payload.ticker)
    g = _normalize_group(payload.group_name)
    existing = (
        db.query(UserWatchlist)
        .filter(
            UserWatchlist.user_id == current_user.user_id,
            UserWatchlist.ticker == t,
            UserWatchlist.group_name == g,
        )
        .first()
    )
    if existing:
        return WatchlistEntry(
            ticker=existing.ticker,
            group_name=existing.group_name or DEFAULT_GROUP,
            added_at=existing.created_at,
        )

    new_row = UserWatchlist(user_id=current_user.user_id, ticker=t, group_name=g)
    db.add(new_row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(UserWatchlist)
            .filter(
                UserWatchlist.user_id == current_user.user_id,
                UserWatchlist.ticker == t,
                UserWatchlist.group_name == g,
            )
            .first()
        )
        if existing:
            return WatchlistEntry(
                ticker=existing.ticker,
                group_name=existing.group_name or DEFAULT_GROUP,
                added_at=existing.created_at,
            )
        raise HTTPException(status_code=500, detail="추가 중 충돌이 발생했습니다.")

    db.refresh(new_row)
    return WatchlistEntry(
        ticker=new_row.ticker,
        group_name=new_row.group_name or DEFAULT_GROUP,
        added_at=new_row.created_at,
    )


@router.delete(
    "/{ticker}",
    summary="관심종목 삭제 — group_name 미지정 시 모든 그룹에서 삭제",
)
def remove_watchlist(
    ticker: str,
    group_name: Optional[str] = Query(
        None,
        description=(
            "그룹 지정 시 해당 그룹에서만 삭제. "
            "미지정 시 모든 그룹에서 삭제 — 응답의 deleted_count·deleted_groups 로 확인."
        ),
    ),
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """이전 구현은 204 No Content 만 반환해 클라이언트가 "한 그룹에서만 지워졌다"
    고 오해할 수 있었다 — 실제로는 group_name 미지정 시 N개 그룹에서 동시 삭제.
    이제 200 + 삭제된 그룹 목록을 명시적으로 반환한다.
    """
    t = _normalize_ticker(ticker)
    q = db.query(UserWatchlist).filter(
        UserWatchlist.user_id == current_user.user_id,
        UserWatchlist.ticker == t,
    )
    if group_name is not None:
        q = q.filter(UserWatchlist.group_name == _normalize_group(group_name))

    # 삭제 전 영향 그룹 캡처
    affected = [(row.group_name or DEFAULT_GROUP) for row in q.all()]
    deleted = q.delete(synchronize_session=False)
    db.commit()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="해당 관심종목이 없습니다.")
    return {
        "ticker":         t,
        "deleted_count":  int(deleted),
        "deleted_groups": affected,
        "scope":          "single_group" if group_name is not None else "all_groups",
    }


@router.patch(
    "/{ticker}/group",
    response_model=WatchlistEntry,
    summary="관심종목의 그룹 변경 (P0-3)",
)
def change_group(
    ticker: str,
    payload: GroupChangeRequest,
    from_group: Optional[str] = Query(None, description="원래 그룹 (미지정 시 동일 ticker 중 가장 최근 1개 이동)"),
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """기존 그룹 → 새 그룹으로 이동. 같은 ticker 가 여러 그룹에 있으면 from_group 으로 지정."""
    t = _normalize_ticker(ticker)
    new_g = _normalize_group(payload.group_name)
    q = db.query(UserWatchlist).filter(
        UserWatchlist.user_id == current_user.user_id,
        UserWatchlist.ticker == t,
    )
    if from_group is not None:
        q = q.filter(UserWatchlist.group_name == _normalize_group(from_group))
    row = q.order_by(UserWatchlist.created_at.desc()).first()
    if not row:
        raise HTTPException(status_code=404, detail="해당 관심종목이 없습니다.")

    if row.group_name == new_g:
        return WatchlistEntry(
            ticker=row.ticker,
            group_name=row.group_name or DEFAULT_GROUP,
            added_at=row.created_at,
        )

    row.group_name = new_g
    try:
        db.commit()
    except IntegrityError:
        # 새 그룹에 이미 동일 ticker 존재 — 409 로 반환해 클라이언트가 머지·교체를 결정.
        # 이전 구현은 이동 row 를 silent 하게 삭제하고 200 으로 응답 → 사용자가
        # "이동 성공" 으로 오해하지만 실제로는 데이터 한 건이 사라졌다.
        db.rollback()
        existing_target = (
            db.query(UserWatchlist)
            .filter(
                UserWatchlist.user_id == current_user.user_id,
                UserWatchlist.ticker == t,
                UserWatchlist.group_name == new_g,
            )
            .first()
        )
        raise HTTPException(
            status_code=409,
            detail={
                "code":    "WATCHLIST_DUPLICATE",
                "message": f"이미 '{new_g}' 그룹에 같은 종목이 있습니다. 원본은 그대로 유지됩니다.",
                "existing": {
                    "ticker":     t,
                    "group_name": new_g,
                    "added_at":   existing_target.created_at.isoformat() if existing_target and existing_target.created_at else None,
                },
            },
        )

    # 정상 commit — row 가 이동됨. refresh 후 반환.
    db.refresh(row)
    return WatchlistEntry(
        ticker=row.ticker,
        group_name=row.group_name or DEFAULT_GROUP,
        added_at=row.created_at,
    )


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
    g = _normalize_group(payload.group_name)
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
                UserWatchlist.group_name == g,
            )
            .first()
        )
        if exists:
            continue
        db.add(UserWatchlist(user_id=current_user.user_id, ticker=t, group_name=g))
        inserted += 1
    if inserted:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()

    rows = (
        db.query(UserWatchlist)
        .filter(UserWatchlist.user_id == current_user.user_id)
        .order_by(UserWatchlist.created_at.desc())
        .all()
    )
    items = [
        WatchlistEntry(
            ticker=r.ticker,
            group_name=r.group_name or DEFAULT_GROUP,
            added_at=r.created_at or datetime.utcnow(),
        )
        for r in rows
    ]
    return WatchlistResponse(total=len(items), items=items)
