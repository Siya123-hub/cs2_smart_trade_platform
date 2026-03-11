# -*- coding: utf-8 -*-
"""
通知推送服务
支持WebSocket实时推送和消息队列

注意: WebSocketManager 已移至 websocket_manager.py 增强版
"""
from typing import Dict, List, Set, Optional
from datetime import datetime
from enum import Enum
import logging
import asyncio

from app.services.websocket_manager import WebSocketManager as EnhancedWebSocketManager

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """通知类型"""
    ORDER = "order"           # 订单通知
    PRICE_ALERT = "price"     # 价格提醒
    INVENTORY = "inventory"   # 库存通知
    MONITOR = "monitor"       # 监控通知
    SYSTEM = "system"         # 系统通知
    TRADE = "trade"           # 交易通知


class NotificationPriority(str, Enum):
    """通知优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# 使用增强版 WebSocketManager (来自 websocket_manager.py)
ws_manager = EnhancedWebSocketManager()


def _get_global_ws_manager() -> EnhancedWebSocketManager:
    """获取全局WebSocket管理器实例"""
    return ws_manager


class NotificationService:
    """通知服务"""
    
    def __init__(self, ws_manager: EnhancedWebSocketManager = None):
        # 使用传入的ws_manager，否则使用全局实例
        self.ws_manager = ws_manager if ws_manager is not None else _get_global_ws_manager()
    
    async def send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        content: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[dict] = None
    ):
        """发送通知"""
        message = {
            "type": "notification",
            "notification_type": notification_type.value,
            "title": title,
            "content": content,
            "priority": priority.value,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.ws_manager.send_personal_message(message, user_id)
        
        logger.info(f"Notification sent to user {user_id}: {title}")
    
    async def notify_order_update(self, user_id: int, order_data: dict):
        """订单更新通知"""
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.ORDER,
            title="订单状态更新",
            content=f"订单 #{order_data.get('id')} 状态已更新为 {order_data.get('status')}",
            data=order_data,
            priority=NotificationPriority.HIGH
        )
    
    async def notify_price_alert(self, user_id: int, item_name: str, current_price: float, target_price: float):
        """价格提醒通知"""
        direction = "上涨" if current_price > target_price else "下跌"
        
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.PRICE_ALERT,
            title=f"价格{direction}提醒",
            content=f"{item_name} 当前价格 ¥{current_price:.2f}，已{direction}至目标价格 ¥{target_price:.2f}",
            data={
                "item_name": item_name,
                "current_price": current_price,
                "target_price": target_price,
                "direction": direction
            },
            priority=NotificationPriority.NORMAL
        )
    
    async def notify_inventory_change(self, user_id: int, change_type: str, item_name: str, quantity: int = 1):
        """库存变更通知"""
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.INVENTORY,
            title="库存变更",
            content=f"{item_name} {change_type} {quantity} 件",
            data={
                "item_name": item_name,
                "change_type": change_type,
                "quantity": quantity
            },
            priority=NotificationPriority.NORMAL
        )
    
    async def notify_monitor_triggered(self, user_id: int, monitor_name: str, trigger_data: dict):
        """监控触发通知"""
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.MONITOR,
            title="监控触发",
            content=f"监控 [{monitor_name}] 已触发",
            data=trigger_data,
            priority=NotificationPriority.HIGH
        )
    
    async def notify_system_message(self, user_id: int, title: str, content: str):
        """系统消息通知"""
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.SYSTEM,
            title=title,
            content=content,
            priority=NotificationPriority.NORMAL
        )


# 全局实例 - 使用增强版 WebSocketManager
notification_service = NotificationService(ws_manager)
