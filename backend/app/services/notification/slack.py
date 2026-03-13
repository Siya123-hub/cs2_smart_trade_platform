# -*- coding: utf-8 -*-
"""
Slack 通知渠道
支持 Webhook 推送
"""
import aiohttp
import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import json

from app.services.notification.base import NotificationChannel, Message, ChannelConfig

logger = logging.getLogger(__name__)


class SlackConfig(ChannelConfig):
    """Slack 通知配置"""
    enabled: bool = Field(default=False)
    webhook_url: str = Field(default="", description="Slack Webhook URL")
    username: str = Field(default="CS2 Trader", description="机器人用户名")
    icon_emoji: str = Field(default=":robot_face:", description="机器人图标")
    channel: Optional[str] = Field(default=None, description="默认频道")


class SlackNotification(NotificationChannel):
    """Slack 通知渠道"""
    
    def __init__(self, config: SlackConfig):
        super().__init__(config)
        self.webhook_url = config.webhook_url
        self.username = config.username
        self.icon_emoji = config.icon_emoji
        self.default_channel = config.channel
    
    def _get_level_color(self, level: str) -> str:
        """获取级别对应的颜色"""
        colors = {
            "info": "#3498db",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "success": "#27ae60",
        }
        return colors.get(level, "#3498db")
    
    def _get_level_emoji(self, level: str) -> str:
        """获取级别对应的emoji"""
        emojis = {
            "info": ":information_source:",
            "warning": ":warning:",
            "error": ":x:",
            "success": ":white_check_mark:",
        }
        return emojis.get(level, ":information_source:")
    
    def _create_payload(self, message: Message, channel: Optional[str] = None) -> Dict[str, Any]:
        """创建 Slack 消息载荷"""
        # 主消息
        payload = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {
                    "color": self._get_level_color(message.level),
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{self._get_level_emoji(message.level)} {message.title}",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": message.content
                            }
                        }
                    ]
                }
            ]
        }
        
        # 添加元数据
        if message.metadata:
            fields = []
            for key, value in message.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    fields.append({
                        "type": "mrkdwn",
                        "text": f"*{key}:* {value}"
                    })
            
            if fields:
                payload["attachments"][0]["blocks"].append({
                    "type": "section",
                    "fields": fields[:10]  # Slack限制最多10个fields
                })
        
        # 添加 footer
        payload["attachments"][0]["footer"] = "CS2 智能交易平台"
        payload["attachments"][0]["ts"] = int(message.timestamp.timestamp()) if message.timestamp else None
        
        # 添加 channel
        if channel:
            payload["channel"] = channel
        elif self.default_channel:
            payload["channel"] = self.default_channel
        
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
                    if response.status == 200:
                        self._logger.info("Slack notification sent successfully")
                        return True
                    else:
                        response_text = await response.text()
                        self._logger.error(f"Slack webhook failed: {response.status} - {response_text}")
                        return False
        except asyncio.TimeoutError:
            self._logger.error("Slack webhook request timed out")
            return False
        except Exception as e:
            self._logger.error(f"Failed to send Slack notification: {str(e)}")
            return False
    
    async def send(self, message: Message, recipients: List[str]) -> bool:
        """发送单条 Slack 消息"""
        if not self.enabled:
            self._logger.warning("Slack notification is disabled")
            return False
        
        # Slack 使用 channel 而不是 recipients
        channel = recipients[0] if recipients else self.default_channel
        payload = self._create_payload(message, channel)
        
        return await self._send_webhook(payload)
    
    async def send_batch(self, messages: List[Message], recipients: List[str]) -> bool:
        """批量发送 Slack 消息"""
        if not self.enabled:
            self._logger.warning("Slack notification is disabled")
            return False
        
        success = True
        channel = recipients[0] if recipients else self.default_channel
        
        for message in messages:
            payload = self._create_payload(message, channel)
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
            content="Testing Slack connection",
            level="info"
        )
        
        return await self.send(test_message, [])
