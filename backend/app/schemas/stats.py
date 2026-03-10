# -*- coding: utf-8 -*-
"""
统计 Schema
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from decimal import Decimal


class StatsBase(BaseModel):
    """统计基础"""
    pass


class OverallStats(StatsBase):
    """总体统计"""
    total_users: int = 0
    total_bots: int = 0
    total_orders: int = 0
    total_trades: int = 0
    total_volume: float = 0.0
    active_monitors: int = 0
    inventory_value: float = 0.0


class UserStats(StatsBase):
    """用户统计"""
    user_id: int
    total_orders: int = 0
    completed_orders: int = 0
    cancelled_orders: int = 0
    total_spent: float = 0.0
    total_earned: float = 0.0
    profit: float = 0.0
    inventory_count: int = 0
    inventory_value: float = 0.0


class TradeStats(StatsBase):
    """交易统计"""
    date: str
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_volume: float = 0.0
    avg_trade_value: float = 0.0


class TradeStatsListResponse(BaseModel):
    """交易统计列表响应"""
    trades: List[TradeStats]
    total: int


class ProfitStats(StatsBase):
    """利润统计"""
    period: str
    total_profit: float = 0.0
    arbitrage_profit: float = 0.0
    flip_profit: float = 0.0
    fee: float = 0.0


class ProfitStatsResponse(BaseModel):
    """利润统计响应"""
    daily: Optional[ProfitStats] = None
    weekly: Optional[ProfitStats] = None
    monthly: Optional[ProfitStats] = None
    all_time: Optional[ProfitStats] = None


class InventoryValueStats(BaseModel):
    """库存价值统计"""
    total_value: float = 0.0
    by_platform: dict = {}
    by_rarity: dict = {}
    top_items: List[dict] = []


class PriceTrend(BaseModel):
    """价格趋势"""
    date: str
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    volume: int = 0


class PriceTrendResponse(BaseModel):
    """价格趋势响应"""
    item_id: int
    trends: List[PriceTrend]


class DashboardStats(BaseModel):
    """仪表盘统计"""
    overview: OverallStats
    recent_orders: List[dict] = []
    top_performers: List[dict] = []
    alerts: List[dict] = []
