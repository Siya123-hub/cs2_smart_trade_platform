# -*- coding: utf-8 -*-
"""
WebSocket 通知渠道
"""
from typing import List
import logging

from app.services.notification.channels.base import NotificationChannel, Message
from app.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class WebSocketChannel(NotificationChannel):
    """WebSocket通知渠道"""
    
    def __init__(self, ws_manager: WebSocketManager = None, enabled: bool = True):
        super().__init__(enabled)
        self.ws_manager = ws_manager or WebSocketManager()
    
    async def send(self, message: Message) -> bool:
        """发送单条消息到WebSocket"""
        if not self.enabled:
            return False
        
        try:
            # 从message中获取接收者
            recipients = message.recipients or []
            
            # 转换消息格式
            ws_message = {
                "type": "notification",
                "title": message.title,
                "content": message.content,
                "level": message.level.value,
                "data": message.data or {},
            }
            
            # 发送给所有接收者
            for user_id in recipients:
                await self.ws_manager.send_personal_message(ws_message, int(user_id))
            
            logger.info(f"WebSocket notification sent: {message.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")
            return False
    
    async def send_batch(self, messages: List[Message]) -> bool:
        """批量发送消息"""
        if not self.enabled:
            return False
        
        try:
            results = []
            for msg in messages:
                result = await self.send(msg)
                results.append(result)
            
            return all(results)
            
        except Exception as e:
            logger.error(f"Failed to send batch WebSocket notifications: {e}")
            return False
