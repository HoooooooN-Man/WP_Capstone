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
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User, UserHolding, UserHoldingHistory
from .users import _require_current_user


# ── audit history helper ─────────────────────────────────────────────────────

def _snapshot(row: UserHolding) -> dict:
    """UserHolding row → JSONB-friendly dict."""
    return {
        "id":         row.id,
        "user_id":    row.user_id,
        "ticker":     row.ticker,
        "quantity":   int(row.quantity) if row.quantity is not None else None,
        "avg_price":  str(row.avg_price) if row.avg_price is not None else None,  # Decimal preserved
        "bought_at":  row.bought_at.isoformat() if row.bought_at else None,
        "memo":       row.memo,
        "deleted_at": row.deleted_at.isoformat() if row.deleted_at else None,
    }


def _audit(db: Session, row: UserHolding, action: str) -> None:
    """L#54 — UserHolding 변경을 user_holdings_history 에 박제."""
    db.add(UserHoldingHistory(
        holding_id=row.id,
        user_id=row.user_id,
        action=action,
        snapshot=_snapshot(row),
    ))


router = APIRouter(prefix="/users/me/portfolio", tags=["portfolio"])


# ── 스키마 ────────────────────────────────────────────────────────────────────

class HoldingItem(BaseModel):
    id:         int
    ticker:     str
    quantity:   int
    # M#36: avg_price 는 NUMERIC(20,4). JSON 직렬화는 float — FE 표시 정밀도 유지.
    avg_price:  float
    bought_at:  Optional[date] = None
    memo:       Optional[str] = None
    invested:   float       # quantity * avg_price
    current_price: Optional[float] = None       # FE 가 enrich (선택)
    return_amount: Optional[float] = None
    return_pct:    Optional[float] = None
    signal_label:  Optional[str] = None

    class Config:
        from_attributes = True


class HoldingsSummary(BaseModel):
    total_invested: float
    current_value:  Optional[float] = None      # FE enrich 후 합산
    total_return_amount: Optional[float] = None
    total_return_pct:    Optional[float] = None


class HoldingsResponse(BaseModel):
    total:   int
    items:   List[HoldingItem]
    summary: HoldingsSummary
    is_advice: bool = False                    # 자문 아님 명시 (PRD §9)


# 상한선 — DoS·malformed payload 차단.
# avg_price: M#36 이전엔 KRW 정수였으나 NUMERIC(20,4) 마이그레이션 후 외국 종목 USD 소수 지원.
#            상한은 1억(KRW 종목) 또는 1억 USD(외국 종목) 모두 커버.
# quantity: 일반 개인투자자 기준 1억주 미만으로 충분.
MAX_AVG_PRICE = 100_000_000   # 1억 (단위는 종목 통화 — 한국 KRW / 미국 USD 등)
MAX_QUANTITY  = 100_000_000   # 1억주


class HoldingCreateRequest(BaseModel):
    ticker:    str = Field(..., min_length=1, max_length=20)
    quantity:  int = Field(..., gt=0, le=MAX_QUANTITY)
    # avg_price 는 NUMERIC(20,4) 컬럼에 매핑 — float 입력 허용 (소수점 4자리까지).
    avg_price: float = Field(..., gt=0, le=MAX_AVG_PRICE)
    bought_at: Optional[date] = None
    memo:      Optional[str] = Field(default=None, max_length=200)


class HoldingUpdateRequest(BaseModel):
    quantity:  Optional[int]   = Field(default=None, gt=0, le=MAX_QUANTITY)
    avg_price: Optional[float] = Field(default=None, gt=0, le=MAX_AVG_PRICE)
    bought_at: Optional[date]  = None
    memo:      Optional[str]   = Field(default=None, max_length=200)


def _to_decimal(v) -> Decimal:
    """입력 float/str → 4자리 정밀도 Decimal."""
    return Decimal(str(v)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _normalize_ticker(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="티커가 비어있습니다.")
    return s.zfill(6) if s.isdigit() else s.upper()


def _to_item(h: UserHolding) -> HoldingItem:
    # NUMERIC → float 변환. Decimal → float 캐스트는 응답 정밀도 충분 (소수 4자리).
    ap = float(h.avg_price) if h.avg_price is not None else 0.0
    qty = int(h.quantity) if h.quantity is not None else 0
    return HoldingItem(
        id=h.id,
        ticker=h.ticker,
        quantity=qty,
        avg_price=ap,
        bought_at=h.bought_at,
        memo=h.memo,
        invested=qty * ap,
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
    # L#54: soft delete 적용 — deleted_at NULL 만 노출.
    rows = (
        db.query(UserHolding)
        .filter(
            UserHolding.user_id == current_user.user_id,
            UserHolding.deleted_at.is_(None),
        )
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
    summary="보유 종목 추가 — mode=merge(기본): 평단 합산 / mode=reject: 중복 시 409",
)
def add_holding(
    payload: HoldingCreateRequest,
    mode: str = Query(
        "merge",
        pattern="^(merge|reject)$",
        description="merge: 동일 ticker 면 평균단가 합산(기본·기존 동작) / reject: 중복이면 409 반환",
    ),
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """동일 ticker 중복 시 동작은 `mode` 로 명시한다.

      - **merge (default)** — 평균단가 자동 합산. memo/bought_at 은 기존 값이 있으면
        유지 (이전 구현이 memo 를 silent 하게 덮어쓰던 동작은 폐기).
        new_avg = (old.q × old.p + new.q × new.p) / (old.q + new.q)
      - **reject** — 이미 동일 ticker 가 있으면 409 반환. FE 에서 PATCH 로 명시적 수정.
    """
    t = _normalize_ticker(payload.ticker)

    # active(soft-not-deleted) row 만 중복 판단 대상.
    existing = (
        db.query(UserHolding)
        .filter(
            UserHolding.user_id == current_user.user_id,
            UserHolding.ticker == t,
            UserHolding.deleted_at.is_(None),
        )
        .first()
    )

    new_avg_price = _to_decimal(payload.avg_price)

    if existing:
        if mode == "reject":
            raise HTTPException(
                status_code=409,
                detail={
                    "code":    "HOLDING_DUPLICATE",
                    "message": "이미 같은 종목을 보유 중입니다. 수정하려면 PATCH 를 사용하세요.",
                    "existing_id": existing.id,
                },
            )
        # mode == merge — 평단가 합산 (Decimal 산술, 잘림 없음).
        old_qty = Decimal(int(existing.quantity))
        old_avg = Decimal(str(existing.avg_price))
        add_qty = Decimal(int(payload.quantity))
        total_old = old_qty * old_avg
        total_new = add_qty * new_avg_price
        new_qty   = int(existing.quantity + payload.quantity)
        merged    = ((total_old + total_new) / Decimal(new_qty)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        existing.quantity = new_qty
        existing.avg_price = merged
        if payload.bought_at and not existing.bought_at:
            existing.bought_at = payload.bought_at
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=500, detail="추가 중 충돌이 발생했습니다.")
        db.refresh(existing)
        _audit(db, existing, "updated")
        db.commit()
        return _to_item(existing)

    new_row = UserHolding(
        user_id=current_user.user_id,
        ticker=t,
        quantity=payload.quantity,
        avg_price=new_avg_price,
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
    _audit(db, new_row, "created")
    db.commit()
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
            UserHolding.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="해당 보유 종목이 없습니다.")

    if payload.quantity is not None:
        row.quantity = payload.quantity
    if payload.avg_price is not None:
        row.avg_price = _to_decimal(payload.avg_price)
    if payload.bought_at is not None:
        row.bought_at = payload.bought_at
    if payload.memo is not None:
        row.memo = payload.memo
    row.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    _audit(db, row, "updated")
    db.commit()
    return _to_item(row)


@router.delete(
    "/holdings/{holding_id}",
    summary="보유 종목 삭제 (soft delete — user_holdings_history 에 audit 박제)",
)
def delete_holding(
    holding_id: int,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """L#54: hard-delete → soft delete.

    deleted_at 을 set 하고 user_holdings_history 에 'deleted' 액션 박제. 실수 삭제
    복구 가능 (DB 측 RESTORE 쿼리). 응답 200 + deleted_at 명시.
    """
    row = (
        db.query(UserHolding)
        .filter(
            UserHolding.id == holding_id,
            UserHolding.user_id == current_user.user_id,
            UserHolding.deleted_at.is_(None),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="해당 보유 종목이 없습니다.")
    now = datetime.utcnow()
    row.deleted_at = now
    db.commit()
    db.refresh(row)
    _audit(db, row, "deleted")
    db.commit()
    return {"id": row.id, "ticker": row.ticker, "deleted_at": now.isoformat()}
