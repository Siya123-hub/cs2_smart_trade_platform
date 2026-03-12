# -*- coding: utf-8 -*-
"""
订单模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class Order(Base):
    """订单模型"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(100), unique=True, index=True)  # 外部订单号
    
    # 用户
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # 饰品
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    
    # 订单信息
    side = Column(String(10), nullable=False)  # 'buy' / 'sell'
    price = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Integer, default=1)
    
    # 状态
    status = Column(String(20), default='pending', index=True)  # pending/completed/cancelled/failed
    
    # 来源
    source = Column(String(20), nullable=False)  # 'steam' / 'buff' / 'manual'
    
    # 外部ID
    external_id = Column(String(100), nullable=True)
    
    # 备注
    remark = Column(String(500), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # 关联
    user = relationship("User", back_populates="orders")
    item = relationship("Item", back_populates="orders")

    # 索引
    __table_args__ = (
        Index("idx_orders_user_status", "user_id", "status"),
        Index("idx_orders_created", "created_at"),
    )

    def __repr__(self):
        return f"<Order {self.order_id} {self.side} {self.price}>"


class OrderLog(Base):
    """订单日志"""
    __tablename__ = "order_logs"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    
    # 日志内容
    action = Column(String(50), nullable=False)  # created/updated/completed/cancelled
    message = Column(String(500), nullable=True)
    details = Column(String(1000), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    # 索引
    __table_args__ = (
        Index("idx_order_logs_order_id", "order_id"),
    )
