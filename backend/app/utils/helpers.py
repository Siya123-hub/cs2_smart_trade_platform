# -*- coding: utf-8 -*-
"""
工具函数
"""
from typing import Any, Dict, Optional
import json
from datetime import datetime, date


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """格式化日期时间"""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date(d: Optional[date]) -> Optional[str]:
    """格式化日期"""
    if d is None:
        return None
    return d.strftime("%Y-%m-%d")


def parse_json_safe(json_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """安全解析 JSON"""
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def to_json_safe(obj: Any) -> str:
    """安全转换为 JSON"""
    if obj is None:
        return None
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return None


def truncate_string(s: str, max_length: int = 100) -> str:
    """截断字符串"""
    if len(s) <= max_length:
        return s
    return s[:max_length - 3] + "..."
