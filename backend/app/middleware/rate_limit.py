# -*- coding: utf-8 -*-
"""
速率限制中间件 - API 限流
"""
import time
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    速率限制中间件
    
    支持按端点配置不同的限流规则:
    - 登录端点: 严格限制（防暴力破解）
    - API端点: 一般限制
    - 监控端点: 宽松限制
    
    限流策略:
    - 基于 IP + 端点的双重限制
    - 滑动窗口算法
    - 可配置 burst（突发）限制
    """
    
    def __init__(self, app, config: Optional[Dict] = None):
        super().__init__(app)
        # 默认限流配置
        self.default_config = {
            "requests": 60,      # 默认每分钟60次
            "window": 60,        # 窗口60秒
            "burst": 10,         # 突发限制10次
        }
        # 端点特定配置
        self.endpoint_config = config or {
            "/api/v1/auth/login": {
                "requests": 5,
                "window": 60,
                "burst": 3,
                "description": "登录端点严格限制"
            },
            "/api/v1/auth/register": {
                "requests": 3,
                "window": 300,
                "burst": 1,
                "description": "注册端点更严格限制"
            },
            "/api/v1/orders": {
                "requests": 120,
                "window": 60,
                "burst": 20,
                "description": "订单端点中等限制"
            },
            "/api/v1/monitoring": {
                "requests": 300,
                "window": 60,
                "burst": 50,
                "description": "监控端点宽松限制"
            },
            "/api/v1/bots": {
                "requests": 100,
                "window": 60,
                "burst": 15,
                "description": "机器人端点中等限制"
            },
        }
        # 存储请求记录: {key: [timestamp1, timestamp2, ...]}
        self._requests: Dict[str, list] = defaultdict(list)
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _get_rate_limit_key(self, request: Request, endpoint: str) -> str:
        """生成限流key"""
        client_ip = self._get_client_ip(request)
        return f"{client_ip}:{endpoint}"
    
    def _get_endpoint_config(self, path: str) -> Dict:
        """获取端点限流配置"""
        # 精确匹配
        if path in self.endpoint_config:
            return self.endpoint_config[path]
        
        # 前缀匹配
        for endpoint, config in self.endpoint_config.items():
            if path.startswith(endpoint):
                return config
        
        return self.default_config
    
    def _check_rate_limit(self, key: str, config: Dict) -> Tuple[bool, Optional[Dict]]:
        """
        检查是否超过限流
        
        返回: (是否允许, 超限信息)
        """
        current_time = time.time()
        window = config["window"]
        requests_limit = config["requests"]
        burst_limit = config.get("burst", requests_limit)
        
        # 清理过期记录
        if key in self._requests:
            self._requests[key] = [
                ts for ts in self._requests[key]
                if current_time - ts < window
            ]
        
        request_times = self._requests[key]
        recent_count = len(request_times)
        
        # 检查是否超过限制
        if recent_count >= requests_limit:
            # 计算剩余时间
            oldest = request_times[0]
            retry_after = int(window - (current_time - oldest)) + 1
            
            logger.warning(f"Rate limit exceeded for {key}: {recent_count}/{requests_limit}")
            
            return False, {
                "requests": recent_count,
                "limit": requests_limit,
                "window": window,
                "retry_after": retry_after,
            }
        
        # 检查突发限制
        if recent_count >= burst_limit:
            # 接近限制，警告但不阻止
            logger.info(f"Rate limit warning for {key}: {recent_count}/{burst_limit}")
        
        # 记录本次请求
        request_times.append(current_time)
        
        return True, None
    
    async def dispatch(self, request: Request, call_next):
        # 只对 API 端点进行限流
        path = request.url.path
        
        if not path.startswith("/api/"):
            return await call_next(request)
        
        # 获取配置
        config = self._get_endpoint_config(path)
        key = self._get_rate_limit_key(request, path)
        
        # 检查限流
        allowed, info = self._check_rate_limit(key, config)
        
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "请求过于频繁，请稍后重试",
                    "error": "rate_limit_exceeded",
                    "retry_after": info["retry_after"],
                }
            )
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + info["retry_after"])
            response.headers["Retry-After"] = str(info["retry_after"])
            return response
        
        # 处理请求
        response = await call_next(request)
        
        # 添加限流头
        if key in self._requests:
            remaining = config["requests"] - len(self._requests[key])
            response.headers["X-RateLimit-Limit"] = str(config["requests"])
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + config["window"])
        
        return response


def create_rate_limit_middleware(config: Optional[Dict] = None):
    """创建限流中间件的工厂函数"""
    def middleware(app):
        return RateLimitMiddleware(app, config)
    return middleware
