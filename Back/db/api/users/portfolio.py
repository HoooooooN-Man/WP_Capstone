"""
api/users/portfolio.py
======================
PRD §3.6 / FE §4.13 — 사용자 포트폴리오 (보유 종목) CRUD.

엔드포인트:
  GET    /users/me/portfolio/holdings        — 보유 종목 목록 + 수익률 요약
  POST   /users/me/portfolio/holdings        — 종목 추가 (idempotent: 같은 ticker → 수량 추가 합산)
  PATCH  /users/me/portfolio/holdings/{id}   — 수정 (수량/평단가/메모)
  DELETE /users/me/portfolio/holdings/{id}   — 삭제

응답 필드 (FE 매핑용):
  items[]: { id, ticker, name, quantity, avg_price, current_price,
             return_amount, return_pct, signal_label }
  summary: { total_invested, current_value, total_return_amount, total_return_pct }

설계:
- 보유 종목과 watchlist 분리 (PRD 명시).
- 현재가는 8001 ML API 가 들고있는 prices 테이블 — 본 라우터에서 별도 조회는 안 하고
  현재가/신호 라벨은 FE 가 batch-diagnosis 로 enrich 하거나 평균가 기준 평가만 반환.
- 캡스톤 범위: 본 서비스는 자문 아님 — items 응답에 `is_advice: false` 명시.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User, UserHolding
from .users import _require_current_user


router = APIRouter(prefix="/users/me/portfolio", tags=["portfolio"])


# ── 스키마 ────────────────────────────────────────────────────────────────────

class HoldingItem(BaseModel):
    id:         int
    ticker:     str
    quantity:   int
    avg_price:  int
    bought_at:  Optional[date] = None
    memo:       Optional[str] = None
    invested:   int        # quantity * avg_price
    current_price: Optional[int] = None        # FE 가 enrich (선택)
    return_amount: Optional[int] = None
    return_pct:    Optional[float] = None
    signal_label:  Optional[str] = None

    class Config:
        from_attributes = True


class HoldingsSummary(BaseModel):
    total_invested: int
    current_value:  Optional[int] = None       # FE enrich 후 합산
    total_return_amount: Optional[int] = None
    total_return_pct:    Optional[float] = None


class HoldingsResponse(BaseModel):
    total:   int
    items:   List[HoldingItem]
    summary: HoldingsSummary
    is_advice: bool = False                    # 자문 아님 명시 (PRD §9)


class HoldingCreateRequest(BaseModel):
    ticker:    str = Field(..., min_length=1, max_length=20)
    quantity:  int = Field(..., gt=0)
    avg_price: int = Field(..., gt=0)
    bought_at: Optional[date] = None
    memo:      Optional[str] = Field(default=None, max_length=200)


class HoldingUpdateRequest(BaseModel):
    quantity:  Optional[int] = Field(default=None, gt=0)
    avg_price: Optional[int] = Field(default=None, gt=0)
    bought_at: Optional[date] = None
    memo:      Optional[str] = Field(default=None, max_length=200)


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _normalize_ticker(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="티커가 비어있습니다.")
    return s.zfill(6) if s.isdigit() else s.upper()


def _to_item(h: UserHolding) -> HoldingItem:
    return HoldingItem(
        id=h.id,
        ticker=h.ticker,
        quantity=h.quantity,
        avg_price=h.avg_price,
        bought_at=h.bought_at,
        memo=h.memo,
        invested=h.quantity * h.avg_price,
    )


# ── 엔드포인트 ───────────────────────────────────────────────────────────────

@router.get("/holdings", response_model=HoldingsResponse, summary="내 보유 종목 + 수익률 요약")
def list_holdings(
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """현재 사용자의 보유 종목 목록. 현재가/평가금액은 FE 에서 batch-diagnosis 로 enrich.

    응답에는 매수가 기준 invested 합계만 포함. FE 가 현재가를 채워 final UI 계산.
    """
    rows = (
        db.query(UserHolding)
        .filter(UserHolding.user_id == current_user.user_id)
        .order_by(UserHolding.created_at.desc())
        .all()
    )
    items = [_to_item(r) for r in rows]
    total_invested = sum(it.invested for it in items)
    return HoldingsResponse(
        total=len(items),
        items=items,
        summary=HoldingsSummary(total_invested=total_invested),
    )


@router.post(
    "/holdings",
    response_model=HoldingItem,
    status_code=status.HTTP_201_CREATED,
    summary="보유 종목 추가 (같은 ticker 면 평균단가 자동 합산)",
)
def add_holding(
    payload: HoldingCreateRequest,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """idempotent — 같은 ticker 가 이미 있으면 평균단가 재계산:

        new_avg = (old.quantity * old.avg_price + new.quantity * new.avg_price)
                  / (old.quantity + new.quantity)
        new_quantity = old.quantity + new.quantity
    """
    t = _normalize_ticker(payload.ticker)

    existing = (
        db.query(UserHolding)
        .filter(
            UserHolding.user_id == current_user.user_id,
            UserHolding.ticker == t,
        )
        .first()
    )

    if existing:
        # 평단가 합산
        total_old = existing.quantity * existing.avg_price
        total_new = payload.quantity * payload.avg_price
        existing.quantity = existing.quantity + payload.quantity
        existing.avg_price = int((total_old + total_new) / existing.quantity)
        if payload.memo:
            existing.memo = payload.memo
        if payload.bought_at and not existing.bought_at:
            existing.bought_at = payload.bought_at
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=500, detail="추가 중 충돌이 발생했습니다.")
        db.refresh(existing)
        return _to_item(existing)

    new_row = UserHolding(
        user_id=current_user.user_id,
        ticker=t,
        quantity=payload.quantity,
        avg_price=payload.avg_price,
        bought_at=payload.bought_at,
        memo=payload.memo,
    )
    db.add(new_row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="추가 중 충돌이 발생했습니다.")
    db.refresh(new_row)
    return _to_item(new_row)


@router.patch("/holdings/{holding_id}", response_model=HoldingItem, summary="보유 종목 수정")
def update_holding(
    holding_id: int,
    payload: HoldingUpdateRequest,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(UserHolding)
        .filter(
            UserHolding.id == holding_id,
            UserHolding.user_id == current_user.user_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="해당 보유 종목이 없습니다.")

    if payload.quantity is not None:
        row.quantity = payload.quantity
    if payload.avg_price is not None:
        row.avg_price = payload.avg_price
    if payload.bought_at is not None:
        row.bought_at = payload.bought_at
    if payload.memo is not None:
        row.memo = payload.memo
    row.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return _to_item(row)


@router.delete(
    "/holdings/{holding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="보유 종목 삭제",
)
def delete_holding(
    holding_id: int,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    deleted = (
        db.query(UserHolding)
        .filter(
            UserHolding.id == holding_id,
            UserHolding.user_id == current_user.user_id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="해당 보유 종목이 없습니다.")
    return None
