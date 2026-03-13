# -*- coding: utf-8 -*-
"""
通知管理器
统一管理所有通知渠道
"""
from typing import List, Dict, Optional, Any
import logging
import os

from app.services.notification.channels.base import NotificationChannel, Message, MessageLevel
from app.services.notification.channels.websocket import WebSocketChannel
from app.services.notification.channels.email import EmailChannel
from app.services.notification.channels.slack import SlackChannel
from app.services.notification.channels.discord import DiscordChannel
from app.services.notification.channels.telegram import TelegramChannel

logger = logging.getLogger(__name__)


class NotificationManager:
    """通知管理器"""
    
    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {}
        self._init_channels()
    
    def _init_channels(self):
        """初始化所有通知渠道"""
        # WebSocket
        self.channels["websocket"] = WebSocketChannel(enabled=True)
        
        # Email
        self.channels["email"] = EmailChannel(
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME"),
            password=os.getenv("SMTP_PASSWORD"),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            from_address=os.getenv("SMTP_FROM"),
            enabled=bool(os.getenv("SMTP_HOST"))
        )
        
        # Slack
        self.channels["slack"] = SlackChannel(
            webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            enabled=bool(os.getenv("SLACK_WEBHOOK_URL"))
        )
        
        # Discord
        self.channels["discord"] = DiscordChannel(
            webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
            enabled=bool(os.getenv("DISCORD_WEBHOOK_URL"))
        )
        
        # Telegram
        self.channels["telegram"] = TelegramChannel(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            chat_ids=os.getenv("TELEGRAM_CHAT_IDS", "").split(","),
            enabled=bool(os.getenv("TELEGRAM_BOT_TOKEN"))
        )
        
        logger.info(f"Initialized {len(self.channels)} notification channels")
    
    def get_channel(self, name: str) -> Optional[NotificationChannel]:
        """获取指定渠道"""
        return self.channels.get(name)
    
    def enable_channel(self, name: str):
        """启用渠道"""
        if name in self.channels:
            self.channels[name].enabled = True
            logger.info(f"Enabled notification channel: {name}")
    
    def disable_channel(self, name: str):
        """禁用渠道"""
        if name in self.channels:
            self.channels[name].enabled = False
            logger.info(f"Disabled notification channel: {name}")
    
    def get_enabled_channels(self) -> List[str]:
        """获取已启用的渠道列表"""
        return [name for name, ch in self.channels.items() if ch.enabled]
    
    async def send(
        self,
        message: Message,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        发送通知到指定渠道
        
        Args:
            message: 消息对象
            channels: 指定渠道列表，None表示发送到所有启用渠道
            
        Returns:
            各渠道发送结果
        """
        if channels is None:
            channels = self.get_enabled_channels()
        
        results = {}
        for channel_name in channels:
            channel = self.get_channel(channel_name)
            if channel and channel.enabled:
                try:
                    success = await channel.send(message)
                    results[channel_name] = success
                except Exception as e:
                    logger.error(f"Error sending via {channel_name}: {e}")
                    results[channel_name] = False
            else:
                results[channel_name] = False
        
        return results
    
    async def send_to_all(
        self,
        title: str,
        content: str,
        level: MessageLevel = MessageLevel.INFO,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        便捷方法：发送通知到渠道
        
        Args:
            title: 标题
            content: 内容
            level: 消息级别
            data: 额外数据
            channels: 指定渠道
            
        Returns:
            发送结果
        """
        message = Message(
            title=title,
            content=content,
            level=level,
            data=data
        )
        
        return await self.send(message, channels)
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查所有渠道"""
        results = {}
        for name, channel in self.channels.items():
            try:
                results[name] = await channel.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = False
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """获取通知系统状态"""
        return {
            "total_channels": len(self.channels),
            "enabled_channels": len(self.get_enabled_channels()),
            "channels": {
                name: {
                    "enabled": ch.enabled,
                    "class": ch.__class__.__name__
                }
                for name, ch in self.channels.items()
            }
        }


# 全局通知管理器实例
notification_manager = NotificationManager()
