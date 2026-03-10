# -*- coding: utf-8 -*-
"""
用户模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Steam 账户信息
    steam_id = Column(String(64), unique=True, index=True, nullable=True)
    steam_cookie = Column(Text, nullable=True)  # 加密存储
    
    # BUFF 账户信息
    buff_cookie = Column(Text, nullable=True)  # 加密存储
    
    # Steam 令牌 (MaFile JSON)
    ma_file = Column(Text, nullable=True)
    
    # 账户余额
    balance = Column(Numeric(12, 2), default=0)
    
    # 账户状态
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    orders = relationship("Order", back_populates="user")
    inventory = relationship("Inventory", back_populates="user")
    monitors = relationship("MonitorTask", back_populates="user")

    def __repr__(self):
        return f"<User {self.username}>"


class UserSession(Base):
    """用户会话模型"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 索引
    __table_args__ = (
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_token", "token"),
    )
