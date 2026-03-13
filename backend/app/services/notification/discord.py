# -*- coding: utf-8 -*-
"""
Discord 通知渠道
支持 Webhook 推送
"""
import aiohttp
import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

from app.services.notification.base import NotificationChannel, Message, ChannelConfig

logger = logging.getLogger(__name__)


class DiscordConfig(ChannelConfig):
    """Discord 通知配置"""
    enabled: bool = Field(default=False)
    webhook_url: str = Field(default="", description="Discord Webhook URL")
    username: str = Field(default="CS2 Trader", description="机器人用户名")
    avatar_url: Optional[str] = Field(default=None, description="机器人头像URL")


class DiscordNotification(NotificationChannel):
    """Discord 通知渠道"""
    
    def __init__(self, config: DiscordConfig):
        super().__init__(config)
        self.webhook_url = config.webhook_url
        self.username = config.username
        self.avatar_url = config.avatar_url
    
    def _get_level_color(self, level: str) -> int:
        """获取级别对应的颜色 (RGB转整数)"""
        colors = {
            "info": 0x3498db,      # 蓝色
            "warning": 0xf39c12,   # 橙色
            "error": 0xe74c3c,     # 红色
            "success": 0x27ae60,   # 绿色
        }
        return colors.get(level, 0x3498db)
    
    def _get_level_emoji(self, level: str) -> str:
        """获取级别对应的emoji用于mention"""
        emojis = {
            "info": "",
            "warning": "",
            "error": "@everyone",
            "success": "",
        }
        return emojis.get(level, "")
    
    def _create_embed(self, message: Message) -> Dict[str, Any]:
        """创建 Discord Embed"""
        embed = {
            "title": message.title,
            "description": message.content,
            "color": self._get_level_color(message.level),
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "footer": {
                "text": "CS2 智能交易平台"
            }
        }
        
        # 添加元数据为 fields
        if message.metadata:
            fields = []
            for key, value in message.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    fields.append({
                        "name": key,
                        "value": str(value),
                        "inline": True
                    })
            
            if fields:
                embed["fields"] = fields[:25]  # Discord限制最多25个fields
        
        # 添加缩略图（如果有）
        # embed["thumbnail"] = {"url": "..."}
        
        return embed
    
    def _create_payload(self, message: Message, mention: Optional[str] = None) -> Dict[str, Any]:
        """创建 Discord 消息载荷"""
        payload = {
            "username": self.username,
            "embeds": [self._create_embed(message)]
        }
        
        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url
        
        # 添加 mention
        if mention:
            payload["content"] = mention
        
        return payload
    
    async def _send_webhook(self, payload: Dict[str, Any]) -> bool:
        """发送 Webhook 请求"""
        if not self.webhook_url:
            self._logger.error("Webhook URL not configured")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 204 or response.status == 200:
                        self._logger.info("Discord notification sent successfully")
                        return True
                    else:
                        response_text = await response.text()
                        self._logger.error(f"Discord webhook failed: {response.status} - {response_text}")
                        return False
        except asyncio.TimeoutError:
            self._logger.error("Discord webhook request timed out")
            return False
        except Exception as e:
            self._logger.error(f"Failed to send Discord notification: {str(e)}")
            return False
    
    async def send(self, message: Message, recipients: List[str]) -> bool:
        """发送单条 Discord 消息"""
        if not self.enabled:
            self._logger.warning("Discord notification is disabled")
            return False
        
        # Discord 使用 mention 而不是 recipients
        mention = None
        if recipients:
            # 解析 recipients 中的 mention
            mention = " ".join(recipients)
        
        # 如果没有指定 recipients 但消息级别是 error，自动 @everyone
        if not mention and message.level == "error":
            mention = "@everyone"
        
        payload = self._create_payload(message, mention)
        return await self._send_webhook(payload)
    
    async def send_batch(self, messages: List[Message], recipients: List[str]) -> bool:
        """批量发送 Discord 消息"""
        if not self.enabled:
            self._logger.warning("Discord notification is disabled")
            return False
        
        success = True
        mention = " ".join(recipients) if recipients else None
        
        for message in messages:
            # 第一条消息可以带 mention，后续只发 embed
            msg_mention = mention if messages.index(message) == 0 else None
            payload = self._create_payload(message, msg_mention)
            result = await self._send_webhook(payload)
            if not result:
                success = False
            # 添加小延迟避免限流
            await asyncio.sleep(0.1)
        
        return success
    
    async def health_check(self) -> bool:
        """健康检查"""
        if not self.enabled:
            return False
        
        if not self.webhook_url:
            return False
        
        # 尝试发送测试消息
        test_message = Message(
            title="Health Check",
            content="Testing Discord connection",
            level="info"
        )
        
        return await self.send(test_message, [])
