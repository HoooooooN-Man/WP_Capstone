"""
schemas/board.py
================
종목 토론방 Pydantic 요청 / 응답 스키마.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ── 게시글 ────────────────────────────────────────────────────────────────────

class PostCreate(BaseModel):
    """게시글 작성 요청."""
    ticker:    str  = Field(..., min_length=1, max_length=10,  description="종목 코드")
    author_id: str  = Field(..., min_length=1, max_length=50,  description="작성자 ID")
    title:     str  = Field(..., min_length=2, max_length=100, description="제목")
    content:   str  = Field(..., min_length=1, max_length=5000, description="본문")


class PostSummary(BaseModel):
    """게시글 목록용 요약 응답."""
    post_id:       int
    ticker:        str
    author_id:     str
    title:         str
    views:         int
    likes:         int
    comment_count: int
    created_at:    str


class PostDetail(PostSummary):
    """게시글 상세 응답 (본문 포함)."""
    content: str


class PostListResponse(BaseModel):
    """게시글 목록 + 페이지네이션 메타."""
    ticker:    str
    total:     int
    page:      int
    page_size: int
    items:     list[PostSummary]


class DeleteResponse(BaseModel):
    """삭제 결과."""
    post_id: int
    deleted: bool


# ── 댓글 ─────────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    """댓글 작성 요청."""
    post_id:   int  = Field(..., gt=0,        description="게시글 ID")
    author_id: str  = Field(..., min_length=1, max_length=50,   description="작성자 ID")
    content:   str  = Field(..., min_length=1, max_length=2000, description="댓글 내용")


class CommentItem(BaseModel):
    """댓글 단건."""
    comment_id: int
    post_id:    int
    author_id:  str
    content:    str
    created_at: str


class CommentListResponse(BaseModel):
    """댓글 목록 응답."""
    post_id: int
    total:   int
    items:   list[CommentItem]


# ── 좋아요 ────────────────────────────────────────────────────────────────────

class LikeResponse(BaseModel):
    """좋아요 토글 결과."""
    post_id:   int
    author_id: str
    liked:     bool   # True=좋아요 추가, False=취소
    likes:     int    # 현재 좋아요 수
