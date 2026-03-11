# -*- coding: utf-8 -*-
"""
API v2 路由器
"""
from fastapi import APIRouter

router = APIRouter()

# 挂载 v2 端点模块
from app.api.v2 import router as v2_main_router

router.include_router(v2_main_router, tags=["v2-main"])


@router.get("/info")
async def get_version_info():
    """获取 API v2 版本信息"""
    return {
        "version": "v2",
        "description": "CS2 交易平台 API v2 (Beta)",
        "features": [
            "改进的订单处理",
            "增强的市场分析",
            "性能优化",
        ],
    }
