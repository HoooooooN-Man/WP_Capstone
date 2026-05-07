"""
api/users/cohort.py
===================
W2C — 사용자 cohort 조회·갱신.

엔드포인트:
  GET  /users/me/cohort   → {cohort: "balanced" | null}
  PUT  /users/me/cohort   → cohort 변경. body: {cohort: "..." | null}

정책:
  - 인증 필수 (`_require_current_user`).
  - 허용 값: VALID_COHORTS = {conservative, balanced, growth, dividend, value} ∪ {null}.
  - 컴플라이언스 (CLAUDE.md §3.4): "투자자문" 단어 없음. 응답에 `is_advice: false`.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User
from .users import _require_current_user


router = APIRouter(prefix="/users/me/cohort", tags=["cohort"])


# 허용된 cohort 라벨. None 도 별도로 허용 (= balanced 동치).
VALID_LABELS = {"conservative", "balanced", "growth", "dividend", "value"}


class CohortResponse(BaseModel):
    cohort:    Optional[str] = None
    is_advice: bool = False


class CohortUpdate(BaseModel):
    cohort: Optional[str] = Field(None, max_length=20)


@router.get("", response_model=CohortResponse, summary="내 cohort 조회")
def get_cohort(
    current_user: User = Depends(_require_current_user),
):
    return CohortResponse(cohort=current_user.cohort)


@router.put("", response_model=CohortResponse, summary="내 cohort 변경 (None 허용)")
def update_cohort(
    payload: CohortUpdate,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    new_cohort = (payload.cohort or "").strip().lower() or None
    if new_cohort is not None and new_cohort not in VALID_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않은 cohort. 가능: {sorted(VALID_LABELS)} 또는 null.",
        )

    current_user.cohort = new_cohort
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return CohortResponse(cohort=current_user.cohort)
