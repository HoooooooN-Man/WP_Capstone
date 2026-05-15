"""
api/users/notes.py
==================
사용자 투자노트 CRUD — NewsPage 투자노트 탭.

엔드포인트:
  GET    /users/me/notes        — 내 노트 목록 (최신순)
  POST   /users/me/notes        — 노트 작성
  PATCH  /users/me/notes/{id}   — 노트 수정
  DELETE /users/me/notes/{id}   — 노트 삭제
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User, UserNote
from .users import _require_current_user


router = APIRouter(prefix="/users/me/notes", tags=["notes"])


# ── 스키마 ────────────────────────────────────────────────────────────────────

class NoteItem(BaseModel):
    id:         int
    title:      str
    content:    str
    tags:       List[str] = []
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class NotesResponse(BaseModel):
    total: int
    items: List[NoteItem]


class NoteCreateRequest(BaseModel):
    title:   str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    tags:    List[str] = Field(default_factory=list)


class NoteUpdateRequest(BaseModel):
    title:   Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1)
    tags:    Optional[List[str]] = None


def _to_item(n: UserNote) -> NoteItem:
    return NoteItem(
        id=n.id,
        title=n.title,
        content=n.content,
        tags=[t for t in (n.tags or "").split(",") if t],
        created_at=n.created_at.isoformat() if n.created_at else None,
    )


# ── 엔드포인트 ───────────────────────────────────────────────────────────────

@router.get("", response_model=NotesResponse, summary="내 투자노트 목록")
def list_notes(
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(UserNote)
        .filter(UserNote.user_id == current_user.user_id)
        .order_by(UserNote.created_at.desc())
        .all()
    )
    items = [_to_item(r) for r in rows]
    return NotesResponse(total=len(items), items=items)


@router.post("", response_model=NoteItem, status_code=status.HTTP_201_CREATED, summary="투자노트 작성")
def create_note(
    payload: NoteCreateRequest,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    row = UserNote(
        user_id=current_user.user_id,
        title=payload.title.strip(),
        content=payload.content.strip(),
        tags=",".join(t.strip() for t in payload.tags if t.strip()) or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_item(row)


@router.patch("/{note_id}", response_model=NoteItem, summary="투자노트 수정")
def update_note(
    note_id: int,
    payload: NoteUpdateRequest,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(UserNote)
        .filter(UserNote.id == note_id, UserNote.user_id == current_user.user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="노트를 찾을 수 없습니다.")
    if payload.title is not None:
        row.title = payload.title.strip()
    if payload.content is not None:
        row.content = payload.content.strip()
    if payload.tags is not None:
        row.tags = ",".join(t.strip() for t in payload.tags if t.strip()) or None
    db.commit()
    db.refresh(row)
    return _to_item(row)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT, summary="투자노트 삭제")
def delete_note(
    note_id: int,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(UserNote)
        .filter(UserNote.id == note_id, UserNote.user_id == current_user.user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="노트를 찾을 수 없습니다.")
    db.delete(row)
    db.commit()
    return None
