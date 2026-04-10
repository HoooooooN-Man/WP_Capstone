from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    nickname = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # 관계 설정: 유저가 삭제되면 관련 알림/관심종목도 함께 관리 가능
    watchlist = relationship("UserWatchlist", back_populates="owner")
    notifications = relationship("Notification", back_populates="recipient")

class UserWatchlist(Base):
    __tablename__ = "user_watchlist"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    ticker = Column(String, index=True)
    
    owner = relationship("User", back_populates="watchlist")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    ticker = Column(String)
    title = Column(String)
    sentiment_label = Column(String) # FinBERT 결과 저장
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    recipient = relationship("User", back_populates="notifications")