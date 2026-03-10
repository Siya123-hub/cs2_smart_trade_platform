# -*- coding: utf-8 -*-
"""
Steam 相关工具
"""
import re
from typing import Optional


def parse_steam_id(steam_id: str) -> Optional[str]:
    """解析 Steam ID"""
    if not steam_id:
        return None
    
    # 移除空格和特殊字符
    steam_id = steam_id.strip()
    
    # 检查是否是 Steam ID 64
    if steam_id.isdigit():
        return steam_id
    
    # 检查是否是 STEAM_1:1:12345678 格式
    match = re.match(r'STEAM_1:(\d+):(\d+)', steam_id)
    if match:
        is_public = int(match.group(1))
        account_id = int(match.group(2))
        return str(account_id * 2 + (1 if is_public else 0) + 76561197960265728)
    
    return steam_id


def format_steam_id(steam_id: str) -> str:
    """格式化 Steam ID 显示"""
    if not steam_id:
        return ""
    
    # 尝试转换为 STEAM_1:1:12345678 格式
    try:
        steam_id_int = int(steam_id)
        if steam_id_int >= 76561197960265728:
            account_id = steam_id_int - 76561197960265728
            is_public = account_id % 2
            account_number = account_id // 2
            return f"STEAM_1:{is_public}:{account_number}"
    except (ValueError, TypeError):
        pass
    
    return steam_id


def validate_steam_id(steam_id: str) -> bool:
    """验证 Steam ID 是否有效"""
    if not steam_id:
        return False
    
    # 64位 Steam ID
    if steam_id.isdigit() and len(steam_id) == 17:
        return True
    
    # STEAM_1:1:12345678 格式
    if re.match(r'STEAM_1:\d+:\d+', steam_id):
        return True
    
    return False


def get_steam_community_url(steam_id: str) -> str:
    """获取 Steam 社区链接"""
    return f"https://steamcommunity.com/profiles/{steam_id}"


def get_steam_inventory_url(steam_id: str, app_id: int = 730, context_id: int = 2) -> str:
    """获取 Steam 库存链接"""
    return f"https://steamcommunity.com/profiles/{steam_id}/inventory/?l=schinese&appid={app_id}#contextid={context_id}"
