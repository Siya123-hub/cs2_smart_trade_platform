# -*- coding: utf-8 -*-
"""
API 响应格式定义
"""
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime


class ErrorDetail(BaseModel):
    """错误详情"""
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    field: Optional[str] = Field(None, description="出错字段")
    details: Optional[Dict[str, Any]] = Field(None, description="额外详情")


class ValidationErrorResponse(BaseModel):
    """验证错误响应"""
    status: str = "error"
    code: str = "VALIDATION_ERROR"
    message: str = "验证失败"
    errors: List[ErrorDetail] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NotFoundResponse(BaseModel):
    """资源未找到响应"""
    status: str = "error"
    code: str = "NOT_FOUND"
    message: str = "资源不存在"
    resource_type: Optional[str] = None
    resource_id: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UnauthorizedResponse(BaseModel):
    """未授权响应"""
    status: str = "error"
    code: str = "UNAUTHORIZED"
    message: str = "未授权访问"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ForbiddenResponse(BaseModel):
    """禁止访问响应"""
    status: str = "error"
    code: str = "FORBIDDEN"
    message: str = "禁止访问"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class InternalServerErrorResponse(BaseModel):
    """服务器内部错误响应"""
    status: str = "error"
    code: str = "INTERNAL_ERROR"
    message: str = "服务器内部错误"
    request_id: Optional[str] = Field(None, description="请求追踪ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RateLimitResponse(BaseModel):
    """速率限制响应"""
    status: str = "error"
    code: str = "RATE_LIMIT"
    message: str = "请求过于频繁"
    retry_after: Optional[int] = Field(None, description="重试等待秒数")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============ 列表响应 ============

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    status: str = "success"
    data: List[T] = Field(default_factory=list)
    pagination: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ListResponse(BaseModel, Generic[T]):
    """列表响应"""
    status: str = "success"
    data: List[T] = Field(default_factory=list)
    total: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============ 通用响应 ============

class SuccessResponse(BaseModel):
    """通用成功响应"""
    status: str = "success"
    message: str = "操作成功"
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CreatedResponse(BaseModel):
    """创建成功响应"""
    status: str = "success"
    message: str = "创建成功"
    resource_id: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UpdatedResponse(BaseModel):
    """更新成功响应"""
    status: str = "success"
    message: str = "更新成功"
    updated_fields: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DeletedResponse(BaseModel):
    """删除成功响应"""
    status: str = "success"
    message: str = "删除成功"
    deleted_id: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============ 健康检查 ============

class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"


class ReadinessCheckResponse(BaseModel):
    """就绪检查响应"""
    status: str
    checks: Dict[str, str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
