# -*- coding: utf-8 -*-
"""
Slack 通知渠道
使用 Webhook 实现 Slack 消息推送
"""
from typing import List, Optional
import logging
import os
import json

from app.services.notification.channels.base import NotificationChannel, Message

logger = logging.getLogger(__name__)


class SlackChannel(NotificationChannel):
    """Slack通知渠道"""
    
    def __init__(
        self,
        webhook_url: str = None,
        enabled: bool = True,
        username: str = "CS2 Trader",
        icon_emoji: str = ":robot_face:"
    ):
        super().__init__(enabled)
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL", "")
        self.username = username
        self.icon_emoji = icon_emoji
    
    def _build_payload(self, message: Message) -> dict:
        """构建Slack消息载荷"""
        level_colors = {
            "info": "#3498db",
            "success": "#27ae60",
            "warning": "#f39c12",
            "error": "#e74c3c"
        }
        color = level_colors.get(message.level.value, "#3498db")
        
        payload = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [{
                "color": color,
                "title": message.title,
                "text": message.content,
                "footer": "CS2 Smart Trader",
                "ts": int(os.time.time())
            }]
        }
        
        # 添加额外数据作为字段
        if message.data:
            fields = []
            for key, value in message.data.items():
                if isinstance(value, (str, int, float, bool)):
                    fields.append({
                        "title": key,
                        "value": str(value),
                        "short": True
                    })
            if fields:
                payload["attachments"][0]["fields"] = fields
        
        return payload
    
    async def send(self, message: Message) -> bool:
        """发送Slack消息"""
        if not self.enabled:
            return False
        
        if not self.webhook_url:
            logger.warning("Slack webhook not configured")
            return False
        
        try:
            import aiohttp
            
            payload = self._build_payload(message)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    if resp.status == 200:
                        logger.info(f"Slack notification sent: {message.title}")
                        return True
                    else:
                        logger.error(f"Slack API error: {resp.status}")
                        return False
                        
        except ImportError:
            logger.warning("aiohttp not installed, Slack notifications disabled")
            return False
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    async def send_batch(self, messages: List[Message]) -> bool:
        """批量发送Slack消息"""
        if not self.enabled:
            return False
        
        results = []
        for msg in messages:
            result = await self.send(msg)
            results.append(result)
        
        return any(results)
    
    async def health_check(self) -> bool:
        """检查Slack配置"""
        if not self.enabled:
            return False
        return bool(self.webhook_url)
