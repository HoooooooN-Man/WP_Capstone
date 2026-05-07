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

import uuid

from sqlalchemy import (
    Column, Integer, String, Boolean, Text, ForeignKey, DateTime,
    UniqueConstraint, Index,
)
from sqlalchemy import Date as SQLDate
from sqlalchemy.dialects.postgresql import ARRAY, REAL, UUID, JSONB
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
    # W2 — cohort 선택 (None = balanced 와 동치). 미선택 사용자도 정상.
    cohort          = Column(String(20), nullable=True)

    watchlist     = relationship("UserWatchlist", back_populates="owner",     cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="recipient", cascade="all, delete-orphan")
    posts         = relationship("BoardPost",     back_populates="author",    cascade="all, delete-orphan")
    comments      = relationship("BoardComment",  back_populates="author",    cascade="all, delete-orphan")
    likes         = relationship("BoardLike",     back_populates="author",    cascade="all, delete-orphan")
    # impressions: ON DELETE SET NULL — 분석 자산 보존이므로 cascade 없음, back-pop 만.
    # User 삭제 시 impression.user_id 가 NULL 되고 행은 유지.


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


# ── 7~10. W1 events_v1 — 노출·클릭·사후 수익률 로깅 ───────────────────────────
# 출처: 08_recommendation_logic_improvements.md §5.2 + W1A_명세.md
# 결정 박제: user_id INTEGER (기존 users.user_id SERIAL 일관),
#           session_id W7 비로그인 A/B, embedding_version W3.5 이후,
#           impression_outcomes cron(W1D) 이 채움.

class RecommendationImpression(Base):
    __tablename__ = "recommendation_impressions"
    __table_args__ = (
        Index("idx_impressions_user_at",    "user_id",    "shown_at"),
        Index("idx_impressions_session_at", "session_id", "shown_at"),
        Index("idx_impressions_at",         "shown_at"),
    )

    impression_id     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id           = Column(Integer,
                               ForeignKey("users.user_id", ondelete="SET NULL"),
                               nullable=True)
    session_id        = Column(String(64),  nullable=True)
    cohort            = Column(String(20),  nullable=True)
    shown_tickers     = Column(JSONB,       nullable=False)
    model_version     = Column(String(20),  nullable=False)
    embedding_version = Column(String(20),  nullable=True)
    shown_at          = Column(DateTime,    nullable=False, server_default=func.now())
    page_context      = Column(String(50),  nullable=True)

    clicks   = relationship("RecommendationClick",
                            back_populates="impression",
                            cascade="all, delete-orphan")
    outcomes = relationship("ImpressionOutcome",
                            back_populates="impression",
                            cascade="all, delete-orphan")


class RecommendationClick(Base):
    __tablename__ = "recommendation_clicks"
    __table_args__ = (
        Index("idx_clicks_impression", "impression_id"),
        Index("idx_clicks_at",         "clicked_at"),
    )

    click_id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    impression_id   = Column(UUID(as_uuid=True),
                             ForeignKey("recommendation_impressions.impression_id",
                                        ondelete="CASCADE"),
                             nullable=False)
    ticker          = Column(String(10),  nullable=False)
    rank_clicked    = Column(Integer,     nullable=False)
    dwell_ms        = Column(Integer,     nullable=True)
    followup_action = Column(String(30),  nullable=True)
    clicked_at      = Column(DateTime,    nullable=False, server_default=func.now())

    impression = relationship("RecommendationImpression", back_populates="clicks")


class ImpressionOutcome(Base):
    __tablename__ = "impression_outcomes"
    __table_args__ = (
        Index("idx_outcomes_horizon_at", "outcome_horizon_days", "computed_at"),
    )

    impression_id        = Column(UUID(as_uuid=True),
                                  ForeignKey("recommendation_impressions.impression_id",
                                             ondelete="CASCADE"),
                                  primary_key=True)
    outcome_horizon_days = Column(Integer,   primary_key=True)
    ticker_returns       = Column(JSONB,     nullable=False)
    computed_at          = Column(DateTime,  nullable=False, server_default=func.now())

    impression = relationship("RecommendationImpression", back_populates="outcomes")


class EventsV1Meta(Base):
    __tablename__ = "events_v1_meta"

    schema_version = Column(String(20), primary_key=True)
    applied_at     = Column(DateTime,   nullable=False, server_default=func.now())
    notes          = Column(Text,       nullable=True)


# ── 11. W3.5D ticker_embeddings — 종목 임베딩 적재 ────────────────────────────
# 출처: 차기_사이클.md §W3.5
# 정책: PK=ticker (한 시점 한 버전만 활성). 새 버전 학습 시 UPSERT 로 덮어씀.

class TickerEmbedding(Base):
    __tablename__ = "ticker_embeddings"
    __table_args__ = (
        Index("idx_ticker_embeddings_version", "embedding_version"),
    )

    ticker             = Column(String(10), primary_key=True)
    embedding_version  = Column(String(20), nullable=False)
    vector             = Column(ARRAY(REAL), nullable=False)   # 64차원 proj 출력
    computed_at        = Column(DateTime, nullable=False, server_default=func.now())
    data_window_start  = Column(SQLDate, nullable=True)
    data_window_end    = Column(SQLDate, nullable=True)
