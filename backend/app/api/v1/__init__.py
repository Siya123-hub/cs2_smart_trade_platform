# -*- coding: utf-8 -*-
"""
API v1 版本路由
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, items, orders, inventory, monitors, bots, stats, monitoring, market
)

router = APIRouter()

# 注册各模块路由
router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(items.router, prefix="/items", tags=["饰品"])
router.include_router(orders.router, prefix="/orders", tags=["订单"])
router.include_router(inventory.router, prefix="/inventory", tags=["库存"])
router.include_router(monitors.router, prefix="/monitors", tags=["监控"])
router.include_router(bots.router, prefix="/bots", tags=["机器人"])
router.include_router(stats.router, prefix="/stats", tags=["统计"])
router.include_router(monitoring.router, prefix="/monitoring", tags=["监控"])
router.include_router(market.router, prefix="/market", tags=["市场"])
