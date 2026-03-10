# -*- coding: utf-8 -*-
"""
饰品模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Index, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Item(Base):
    """饰品模型"""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    
    # Steam 市场标识
    market_hash_name = Column(String(200), unique=True, index=True, nullable=False)
    app_id = Column(Integer, default=730, index=True)  # CS2 App ID
    
    # 饰品信息
    name = Column(String(200), nullable=False)
    name_cn = Column(String(200), nullable=True)  # 中文名
    rarity = Column(String(50), nullable=True)    # 稀有度
    exterior = Column(String(50), nullable=True)   # 外观 (崭新/久经/...)
    category = Column(String(50), nullable=True)  # 类别 (武器/手套/刀/...)
    quality = Column(String(50), nullable=True)   # 品质 (StatTrak/纪念版/...)
    weapon_id = Column(String(50), nullable=True) # 武器ID
    
    # 图片
    image_url = Column(Text, nullable=True)
    
    # 价格信息
    current_price = Column(Float, default=0)      # 当前售价
    lowest_price = Column(Float, default=0)       # 最低售价
    highest_price = Column(Float, default=0)      # 最高售价
    volume_24h = Column(Integer, default=0)       # 24小时成交量
    
    # Steam 价格
    steam_lowest_price = Column(Float, default=0)
    steam_volume_24h = Column(Integer, default=0)
    
    # 统计
    price_change_24h = Column(Float, default=0)    # 24小时价格变化
    price_change_percent = Column(Float, default=0)
    
    # 时间戳
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    price_history = relationship("PriceHistory", back_populates="item", order_by="desc(PriceHistory.recorded_at)", foreign_keys="PriceHistory.item_id")
    orders = relationship("Order", back_populates="item")
    inventory = relationship("Inventory", back_populates="item")

    def __repr__(self):
        return f"<Item {self.name}>"


class PriceHistory(Base):
    """价格历史模型"""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    
    # 价格来源
    source = Column(String(20), nullable=False)  # 'buff' / 'steam'
    
    # 价格
    price = Column(Float, nullable=False)
    
    # 时间戳
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关联
    item = relationship("Item", back_populates="price_history")

    # 索引
    __table_args__ = (
        Index("idx_price_history_item_time", "item_id", "recorded_at"),
    )

    def __repr__(self):
        return f"<PriceHistory item={self.item_id} price={self.price} source={self.source}>"


class RareItem(Base):
    """稀有饰品监控表"""
    __tablename__ = "rare_items"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, nullable=False, index=True)
    
    # 监控配置
    min_float = Column(Float, nullable=True)     # 最小磨损
    max_float = Column(Float, nullable=True)      # 最大磨损
    is_stattrak = Column(Integer, default=0)     # 是否 StatTrak
    is_souvenir = Column(Integer, default=0)     # 是否纪念版
    
    # 通知配置
    notify_below_price = Column(Float, nullable=True)  # 价格低于时通知
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
