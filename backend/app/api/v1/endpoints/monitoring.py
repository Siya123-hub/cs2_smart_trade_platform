# -*- coding: utf-8 -*-
"""
监控端点 - 健康检查和指标
"""
import time
import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Request
from collections import defaultdict

from app.services.cache import get_cache

logger = logging.getLogger(__name__)

router = APIRouter()

# ============ 指标存储 ============

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self._api_calls: Dict[str, int] = defaultdict(int)
        self._response_times: Dict[str, list] = defaultdict(list)
        self._start_time = time.time()
        self._lock = None  # 简化版本不使用锁
    
    def record_api_call(self, endpoint: str):
        """记录 API 调用"""
        self._api_calls[endpoint] += 1
    
    def record_response_time(self, endpoint: str, duration_ms: float):
        """记录响应时间"""
        # 只保留最近1000条记录
        times = self._response_times[endpoint]
        times.append(duration_ms)
        if len(times) > 1000:
            times.pop(0)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        # 计算平均响应时间
        avg_times = {}
        for endpoint, times in self._response_times.items():
            if times:
                avg_times[endpoint] = round(sum(times) / len(times), 2)
        
        # 缓存统计
        cache_stats = get_cache().get_stats()
        
        return {
            "api_calls": dict(self._api_calls),
            "total_api_calls": sum(self._api_calls.values()),
            "response_times_ms": avg_times,
            "cache_stats": cache_stats,
            "uptime_seconds": int(time.time() - self._start_time),
            "timestamp": datetime.now().isoformat(),
        }
    
    def reset(self):
        """重置指标"""
        self._api_calls.clear()
        self._response_times.clear()
        self._start_time = time.time()


# 全局指标收集器
_metrics = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器实例"""
    return _metrics


# ============ 中间件 ============

async def metrics_middleware(request: Request, call_next):
    """指标收集中间件"""
    start_time = time.time()
    
    # 记录 API 调用
    endpoint = request.url.path
    _metrics.record_api_call(endpoint)
    
    # 处理请求
    response = await call_next(request)
    
    # 记录响应时间
    duration_ms = (time.time() - start_time) * 1000
    _metrics.record_response_time(endpoint, duration_ms)
    
    return response


# ============ 端点 ============

@router.get("/health")
async def health_check():
    """
    健康检查端点
    
    返回服务健康状态
    """
    # 简单检查
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "cs2-trade-platform",
    }


@router.get("/metrics")
async def get_metrics():
    """
    指标端点
    
    返回:
    - API 调用次数
    - 缓存命中率
    - 平均响应时间
    """
    return _metrics.get_metrics()


@router.post("/metrics/reset")
async def reset_metrics():
    """重置指标"""
    _metrics.reset()
    return {"message": "指标已重置"}
