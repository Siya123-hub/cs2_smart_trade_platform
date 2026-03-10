# -*- coding: utf-8 -*-
"""
机器人模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class Bot(Base):
    """交易机器人模型"""
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    
    # 机器人信息
    name = Column(String(100), nullable=False)
    
    # Steam 账户
    steam_id = Column(String(64), unique=True, index=True, nullable=True)
    username = Column(String(100), nullable=True)  # Steam 用户名
    
    # 认证信息 (加密存储)
    session_token = Column(Text, nullable=True)
    ma_file = Column(Text, nullable=True)  # Steam MaFile JSON
    access_token = Column(Text, nullable=True)
    
    # 状态
    status = Column(String(20), default='offline', index=True)  # offline/online/trading/error
    
    # 统计
    inventory_count = Column(Integer, default=0)
    total_trades = Column(Integer, default=0)
    successful_trades = Column(Integer, default=0)
    
    # 最后活动时间
    last_activity = Column(DateTime, nullable=True)
    last_trade_time = Column(DateTime, nullable=True)
    
    # 错误信息
    last_error = Column(String(500), nullable=True)
    
    # 拥有者
    owner_id = Column(Integer, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    # monitor_tasks = relationship("MonitorTask", back_populates="bot")

    def __repr__(self):
        return f"<Bot {self.name} status={self.status}>"


class BotTrade(Base):
    """机器人交易记录"""
    __tablename__ = "bot_trades"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, nullable=False, index=True)
    
    # 交易信息
    trade_offer_id = Column(String(100), unique=True, nullable=True)
    partner_steam_id = Column(String(64), nullable=True)
    
    # 方向
    direction = Column(String(10), nullable=False)  # incoming / outgoing
    
    # 状态
    status = Column(String(20), default='pending', index=True)  # pending/accepted/declined/cancelled
    
    # 饰品
    offered_items = Column(Text, nullable=True)  # JSON
    received_items = Column(Text, nullable=True)  # JSON
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    
    # 索引
    __table_args__ = (
        Index("idx_bot_trades_bot_id", "bot_id"),
        Index("idx_bot_trades_status", "status"),
    )
