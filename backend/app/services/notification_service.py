# -*- coding: utf-8 -*-
"""
通知推送服务
支持WebSocket实时推送和消息队列
"""
from typing import Dict, List, Set, Optional
from fastapi import WebSocket
from datetime import datetime
from enum import Enum
import json
import logging
import asyncio

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


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # user_id -> Set[WebSocket]
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # websocket -> user_id
        self.connection_users: Dict[WebSocket, int] = {}
        # 离线消息队列
        self.offline_messages: Dict[int, List[dict]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """WebSocket连接"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_id
        
        logger.info(f"User {user_id} connected via WebSocket. Total connections: {len(self.active_connections[user_id])}")
        
        # 发送离线消息
        if user_id in self.offline_messages and self.offline_messages[user_id]:
            for message in self.offline_messages[user_id]:
                await self.send_personal_message(message, user_id)
            self.offline_messages[user_id] = []
    
    def disconnect(self, websocket: WebSocket):
        """WebSocket断开"""
        user_id = self.connection_users.pop(websocket, None)
        
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                logger.info(f"User {user_id} disconnected. All connections closed.")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """发送个人消息"""
        if user_id not in self.active_connections:
            # 存储离线消息
            if user_id not in self.offline_messages:
                self.offline_messages[user_id] = []
            self.offline_messages[user_id].append(message)
            logger.info(f"User {user_id} offline. Message queued.")
            return False
        
        disconnected = set()
        
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                disconnected.add(websocket)
        
        # 清理断开的连接
        for ws in disconnected:
            self.disconnect(ws)
        
        return True
    
    async def broadcast(self, message: dict, exclude_users: Optional[List[int]] = None):
        """广播消息"""
        exclude_set = set(exclude_users or [])
        
        for user_id, connections in self.active_connections.items():
            if user_id in exclude_set:
                continue
            
            for websocket in connections:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to user {user_id}: {e}")
    
    def get_online_users(self) -> List[int]:
        """获取在线用户列表"""
        return list(self.active_connections.keys())
    
    def is_user_online(self, user_id: int) -> bool:
        """检查用户是否在线"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    def get_connection_count(self, user_id: int) -> int:
        """获取用户连接数"""
        return len(self.active_connections.get(user_id, set()))


class NotificationService:
    """通知服务"""
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
    
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


# 全局实例
ws_manager = WebSocketManager()
notification_service = NotificationService(ws_manager)
