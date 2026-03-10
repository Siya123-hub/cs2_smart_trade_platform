# -*- coding: utf-8 -*-
"""
操作日志审计中间件
"""
import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    操作日志审计器
    
    记录关键操作:
    - 认证: 登录、登出、注册
    - 交易: 下单、取消订单
    - 配置: 修改用户配置、修改机器人配置
    - 敏感操作: 删除、导出
    """
    
    # 需要审计的端点模式
    AUDIT_PATTERNS = {
        # 认证相关
        "POST:/api/v1/auth/login": {"action": "user_login", "level": "info"},
        "POST:/api/v1/auth/logout": {"action": "user_logout", "level": "info"},
        "POST:/api/v1/auth/register": {"action": "user_register", "level": "info"},
        
        # 订单相关
        "POST:/api/v1/orders": {"action": "order_create", "level": "info"},
        "DELETE:/api/v1/orders/": {"action": "order_cancel", "level": "info"},
        "POST:/api/v1/orders/": {"action": "order_update", "level": "info"},
        
        # 用户配置相关
        "PUT:/api/v1/auth/me": {"action": "user_update", "level": "info"},
        "PATCH:/api/v1/auth/me": {"action": "user_update", "level": "info"},
        
        # 机器人相关
        "POST:/api/v1/bots": {"action": "bot_create", "level": "info"},
        "DELETE:/api/v1/bots/": {"action": "bot_delete", "level": "warning"},
        "PUT:/api/v1/bots/": {"action": "bot_update", "level": "info"},
        
        # 监控配置
        "POST:/api/v1/monitors": {"action": "monitor_create", "level": "info"},
        "DELETE:/api/v1/monitors/": {"action": "monitor_delete", "level": "warning"},
        
        # 关键操作
        "DELETE:/api/v1/": {"action": "delete", "level": "warning"},
    }
    
    def __init__(self, log_sensitive_data: bool = False):
        self.log_sensitive_data = log_sensitive_data
        # 敏感字段不记录
        self.sensitive_fields = {
            "password", "hashed_password", "secret_key", "token",
            "access_token", "refresh_token", "buff_cookie", "ma_file",
            "encryption_key", "api_key", "steam_session"
        }
    
    def _get_client_info(self, request: Request) -> Dict[str, str]:
        """获取客户端信息"""
        return {
            "ip": request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown"),
            "user_agent": request.headers.get("User-Agent", ""),
        }
    
    def _get_user_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """获取用户信息（从请求中提取）"""
        # 从 request.state 获取（如果中间件已设置）
        if hasattr(request.state, "user_id"):
            return {"user_id": request.state.user_id, "username": getattr(request.state, "username", None)}
        return None
    
    def _mask_sensitive_data(self, data: Dict) -> Dict:
        """脱敏处理"""
        if not self.log_sensitive_data:
            return {k: "***" if k.lower() in self.sensitive_fields else v 
                    for k, v in data.items()}
        return data
    
    def _match_pattern(self, method: str, path: str) -> Optional[Dict]:
        """匹配审计模式"""
        # 精确匹配
        key = f"{method}:{path}"
        if key in self.AUDIT_PATTERNS:
            return self.AUDIT_PATTERNS[key]
        
        # 前缀匹配
        for pattern, config in self.AUDIT_PATTERNS.items():
            pattern_method, pattern_path = pattern.split(":", 1)
            if method == pattern_method and path.startswith(pattern_path.rstrip("/")):
                return config
        
        return None
    
    def log(self, request: Request, response_status: int, duration_ms: float, 
            request_body: Optional[Dict] = None, response_body: Optional[Dict] = None):
        """记录审计日志"""
        # 检查是否需要审计
        audit_config = self._match_pattern(request.method, request.url.path)
        
        if not audit_config:
            return
        
        # 构建审计日志
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": audit_config["action"],
            "level": audit_config["level"],
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "status_code": response_status,
            "duration_ms": round(duration_ms, 2),
            "client": self._get_client_info(request),
        }
        
        # 添加用户信息
        user_info = self._get_user_info(request)
        if user_info:
            audit_entry["user"] = user_info
        
        # 添加请求体（脱敏）
        if request_body:
            audit_entry["request"] = self._mask_sensitive_data(request_body)
        
        # 添加响应体（仅错误时）
        if response_status >= 400 and response_body:
            audit_entry["response"] = response_body
        
        # 记录日志
        log_func = getattr(logger, audit_config["level"], logger.info)
        log_func(f"AUDIT: {audit_entry['action']} - {json.dumps(audit_entry, ensure_ascii=False)}")


# 全局审计日志器
_audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    return _audit_logger


# ============ 中间件 ============

async def audit_middleware(request: Request, call_next):
    """审计中间件"""
    start_time = time.time()
    
    # 尝试解析请求体
    request_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                # 重新设置 body 以便后续读取
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
                
                # 尝试解析 JSON
                try:
                    request_body = json.loads(body.decode())
                except:
                    pass
        except:
            pass
    
    # 处理请求
    response = await call_next(request)
    
    # 记录审计日志
    duration_ms = (time.time() - start_time) * 1000
    _audit_logger.log(
        request, 
        response.status_code, 
        duration_ms,
        request_body=request_body
    )
    
    return response
