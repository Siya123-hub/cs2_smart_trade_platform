# -*- coding: utf-8 -*-
"""
安全头部中间件 - HTTP 安全响应头
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.requests import Request
from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    安全头部中间件
    
    添加以下安全响应头:
    - X-Content-Type-Options: 防止 MIME 类型嗅探
    - X-Frame-Options: 防止点击劫持
    - X-XSS-Protection: XSS 过滤器（兼容旧浏览器）
    - Referrer-Policy: 引用来源策略
    - Permissions-Policy: 权限策略
    - Content-Security-Policy: CSP（仅生产环境）
    - Strict-Transport-Security: HSTS（仅生产环境）
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 基础安全头 - 始终启用
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # 生产环境额外安全头
        if not settings.DEBUG:
            # Content Security Policy
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://buff.163.com https://steamcommunity.com; "
                "frame-ancestors 'none';"
            )
            response.headers["Content-Security-Policy"] = csp_policy
            
            # HSTS - 强制 HTTPS
            hsts_max_age = 31536000  # 1年
            response.headers["Strict-Transport-Security"] = f"max-age={hsts_max_age}; includeSubDomains"
        
        return response
