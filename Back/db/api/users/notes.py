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
from db.models import User, UserNote, UserNoteTag
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


# 본문 상한 — DoS·악성 페이로드 차단. 일반 투자노트 한 편은 충분히 수용.
NOTE_CONTENT_MAX = 20_000


class NoteCreateRequest(BaseModel):
    title:   str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=NOTE_CONTENT_MAX)
    tags:    List[str] = Field(default_factory=list, max_length=20)


class NoteUpdateRequest(BaseModel):
    title:   Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1, max_length=NOTE_CONTENT_MAX)
    tags:    Optional[List[str]] = Field(default=None, max_length=20)


TAG_MAX_LEN = 30  # 태그 한 개당 30자 — UI 칩 표시 한도


def _sanitize_tags(raw: List[str]) -> List[str]:
    """tags 입력을 콤마 제거 + 트림 + 중복 제거 + 길이 캡.

    이전 구현은 comma-joined String(200) 으로 저장하면서 검증 없음 →
      1) 태그 안에 콤마가 있으면 두 개로 쪼개져 lossy.
      2) 200자 cap 에 silent truncate.
    여기서 사전 정리하고, content 도 길이 캡 명시.
    """
    seen: set[str] = set()
    out: list[str] = []
    for t in raw or []:
        if not isinstance(t, str):
            continue
        s = t.replace(",", " ").strip()[:TAG_MAX_LEN]
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= 20:
            break
    return out


def _to_item(n: UserNote) -> NoteItem:
    # M#37: tags 는 이제 user_note_tags 관계로 가져옴. tag_items 는 ordering 기준 정렬.
    return NoteItem(
        id=n.id,
        title=n.title,
        content=n.content,
        tags=[t.tag_text for t in (n.tag_items or [])],
        created_at=n.created_at.isoformat() if n.created_at else None,
    )


def _replace_tags(db: Session, note: UserNote, raw_tags: List[str]) -> None:
    """note 의 태그를 raw_tags 로 교체 — 기존 태그 삭제 후 일괄 INSERT."""
    cleaned = _sanitize_tags(raw_tags)
    # 기존 행 삭제
    db.query(UserNoteTag).filter(UserNoteTag.note_id == note.id).delete(synchronize_session=False)
    # 새 행 삽입 (ordering 0..N-1)
    for i, t in enumerate(cleaned):
        db.add(UserNoteTag(note_id=note.id, tag_text=t, ordering=i))


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
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    # M#37: 태그는 별도 user_note_tags 테이블에 적재.
    _replace_tags(db, row, payload.tags or [])
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
        _replace_tags(db, row, payload.tags)
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
