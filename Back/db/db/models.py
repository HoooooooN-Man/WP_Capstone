"""
db/models.py
============
SQLAlchemy ORM 모델 — wp_capstone 스키마와 1:1 매핑.

테이블:
  - users           : 회원
  - user_watchlist  : 사용자 관심종목 (포트폴리오)
  - notifications   : 알림
  - board_posts     : 게시글
  - board_comments  : 댓글
  - board_likes     : 좋아요
"""

from __future__ import annotations
import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, Text, ForeignKey, DateTime,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


# ── 1. users ──────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    user_id         = Column(Integer, primary_key=True, index=True)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    nickname        = Column(String(50),  unique=True, nullable=False)
    is_active       = Column(Boolean, default=True)
    is_verified     = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    watchlist     = relationship("UserWatchlist", back_populates="owner",     cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="recipient", cascade="all, delete-orphan")
    posts         = relationship("BoardPost",     back_populates="author",    cascade="all, delete-orphan")
    comments      = relationship("BoardComment",  back_populates="author",    cascade="all, delete-orphan")
    likes         = relationship("BoardLike",     back_populates="author",    cascade="all, delete-orphan")
    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    
class SocialAccount(Base):
    __tablename__ = "social_accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False)  # 'google', 'kakao', 'naver'
    social_id = Column(String, nullable=False, unique=True) # 플랫폼 제공 고유 ID
    
    user = relationship("User", back_populates="social_accounts")

# ── 2. user_watchlist (포트폴리오) ────────────────────────────────────────────
class UserWatchlist(Base):
    __tablename__ = "user_watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_watch_user_ticker"),
        Index("idx_watch_user",   "user_id"),
        Index("idx_watch_ticker", "ticker"),
    )

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    ticker     = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="watchlist")


# ── 3. notifications ──────────────────────────────────────────────────────────
class Notification(Base):
    __tablename__ = "notifications"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"))
    ticker          = Column(String(20), nullable=False)
    title           = Column(Text, nullable=False)
    sentiment_label = Column(String(20))
    is_read         = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.datetime.utcnow)

    recipient = relationship("User", back_populates="notifications")


# ── 4. board_posts ────────────────────────────────────────────────────────────
class BoardPost(Base):
    __tablename__ = "board_posts"
    __table_args__ = (
        Index("idx_posts_ticker_created", "ticker", "created_at"),
        Index("idx_posts_author",         "author_id"),
    )

    id         = Column(Integer, primary_key=True, index=True)
    ticker     = Column(String(20),  nullable=False)
    author_id  = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    title      = Column(String(255), nullable=False)
    content    = Column(Text,        nullable=False)
    views      = Column(Integer, nullable=False, default=0)
    likes      = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    author        = relationship("User",         back_populates="posts")
    comment_items = relationship("BoardComment", back_populates="post", cascade="all, delete-orphan")
    like_items    = relationship("BoardLike",    back_populates="post", cascade="all, delete-orphan")


# ── 5. board_comments ─────────────────────────────────────────────────────────
class BoardComment(Base):
    __tablename__ = "board_comments"
    __table_args__ = (
        Index("idx_comments_post", "post_id", "created_at"),
    )

    id         = Column(Integer, primary_key=True, index=True)
    post_id    = Column(Integer, ForeignKey("board_posts.id", ondelete="CASCADE"), nullable=False)
    author_id  = Column(Integer, ForeignKey("users.user_id",  ondelete="CASCADE"), nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    post   = relationship("BoardPost", back_populates="comment_items")
    author = relationship("User",       back_populates="comments")


# ── 6. board_likes (중복 방지) ────────────────────────────────────────────────
class BoardLike(Base):
    __tablename__ = "board_likes"
    __table_args__ = (
        UniqueConstraint("post_id", "author_id", name="uq_like_post_author"),
        Index("idx_likes_post",   "post_id"),
        Index("idx_likes_author", "author_id"),
    )

    id         = Column(Integer, primary_key=True, index=True)
    post_id    = Column(Integer, ForeignKey("board_posts.id", ondelete="CASCADE"), nullable=False)
    author_id  = Column(Integer, ForeignKey("users.user_id",  ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    post   = relationship("BoardPost", back_populates="like_items")
    author = relationship("User",       back_populates="likes")
