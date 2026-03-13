# -*- coding: utf-8 -*-
"""
Discord 通知渠道
使用 Webhook 实现 Discord 消息推送
"""
from typing import List, Optional
import logging
import os

from app.services.notification.channels.base import NotificationChannel, Message

logger = logging.getLogger(__name__)


class DiscordChannel(NotificationChannel):
    """Discord通知渠道"""
    
    def __init__(
        self,
        webhook_url: str = None,
        enabled: bool = True,
        username: str = "CS2 Trader"
    ):
        super().__init__(enabled)
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")
        self.username = username
    
    def _build_embed(self, message: Message) -> dict:
        """构建Discord Embed"""
        level_colors = {
            "info": 3447003,    # 蓝色
            "success": 3066993, # 绿色
            "warning": 15105570, # 橙色
            "error": 15158332   # 红色
        }
        color = level_colors.get(message.level.value, 3447003)
        
        embed = {
            "title": message.title,
            "description": message.content,
            "color": color,
            "footer": {"text": "CS2 Smart Trader"},
            "timestamp": os.environ.get("CURRENT_TIME", "")
        }
        
        # 添加字段
        if message.data:
            fields = []
            for key, value in message.data.items():
                if isinstance(value, (str, int, float, bool)):
                    fields.append({
                        "name": key,
                        "value": str(value),
                        "inline": True
                    })
            if fields:
                embed["fields"] = fields
        
        return embed
    
    async def send(self, message: Message) -> bool:
        """发送Discord消息"""
        if not self.enabled:
            return False
        
        if not self.webhook_url:
            logger.warning("Discord webhook not configured")
            return False
        
        try:
            import aiohttp
            
            embed = self._build_embed(message)
            payload = {
                "username": self.username,
                "embeds": [embed]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    if resp.status == 204 or resp.status == 200:
                        logger.info(f"Discord notification sent: {message.title}")
                        return True
                    else:
                        logger.error(f"Discord API error: {resp.status}")
                        return False
                        
        except ImportError:
            logger.warning("aiohttp not installed, Discord notifications disabled")
            return False
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
    
    async def send_batch(self, messages: List[Message]) -> bool:
        """批量发送Discord消息"""
        if not self.enabled:
            return False
        
        results = []
        for msg in messages:
            result = await self.send(msg)
            results.append(result)
        
        return any(results)
    
    async def health_check(self) -> bool:
        """检查Discord配置"""
        if not self.enabled:
            return False
        return bool(self.webhook_url)
