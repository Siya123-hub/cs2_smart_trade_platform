# -*- coding: utf-8 -*-
"""
通知管理器
统一管理所有通知渠道
"""
import asyncio
from typing import List, Optional, Dict, Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
import logging
import yaml
from pathlib import Path

from app.services.notification.base import NotificationChannel, Message, ChannelConfig, MessageLevel
from app.services.notification.email import EmailNotification, EmailConfig
from app.services.notification.slack import SlackNotification, SlackConfig
from app.services.notification.discord import DiscordNotification, DiscordConfig
from app.services.notification.telegram import TelegramNotification, TelegramConfig

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    """渠道类型"""
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"


class NotificationManagerConfig(BaseModel):
    """通知管理器配置"""
    enabled: bool = Field(default=True, description="是否启用通知系统")
    email: EmailConfig = Field(default_factory=EmailConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)


class Template(BaseModel):
    """消息模板"""
    name: str
    title: str
    content: str
    level: str = "info"


class NotificationManager:
    """通知管理器"""
    
    def __init__(self, config: Optional[NotificationManagerConfig] = None):
        self.config = config or NotificationManagerConfig()
        self.enabled = self.config.enabled
        
        # 初始化各渠道
        self.channels: Dict[ChannelType, NotificationChannel] = {}
        self._init_channels()
        
        # 消息模板
        self.templates: Dict[str, Template] = {}
        
        # 回调函数
        self.on_send: Optional[Callable] = None
    
    def _init_channels(self):
        """初始化所有通知渠道"""
        if self.config.email.enabled:
            self.channels[ChannelType.EMAIL] = EmailNotification(self.config.email)
            logger.info("Email notification channel initialized")
        
        if self.config.slack.enabled:
            self.channels[ChannelType.SLACK] = SlackNotification(self.config.slack)
            logger.info("Slack notification channel initialized")
        
        if self.config.discord.enabled:
            self.channels[ChannelType.DISCORD] = DiscordNotification(self.config.discord)
            logger.info("Discord notification channel initialized")
        
        if self.config.telegram.enabled:
            self.channels[ChannelType.TELEGRAM] = TelegramNotification(self.config.telegram)
            logger.info("Telegram notification channel initialized")
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "NotificationManager":
        """从 YAML 配置文件加载"""
        path = Path(yaml_path)
        if not path.exists():
            logger.warning(f"Config file not found: {yaml_path}, using defaults")
            return cls()
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'notifications' not in data:
            logger.warning("Invalid config format, using defaults")
            return cls()
        
        notif_config = data['notifications']
        
        # 构建配置对象
        config = NotificationManagerConfig(
            enabled=notif_config.get('enabled', True),
            email=EmailConfig(**notif_config.get('channels', {}).get('email', {})),
            slack=SlackConfig(**notif_config.get('channels', {}).get('slack', {})),
            discord=DiscordConfig(**notif_config.get('channels', {}).get('discord', {})),
            telegram=TelegramConfig(**notif_config.get('channels', {}).get('telegram', {})),
        )
        
        return cls(config)
    
    def add_template(self, template: Template):
        """添加消息模板"""
        self.templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[Template]:
        """获取消息模板"""
        return self.templates.get(name)
    
    def create_message_from_template(self, template_name: str, **kwargs) -> Optional[Message]:
        """从模板创建消息"""
        template = self.get_template(template_name)
        if not template:
            return None
        
        return Message(
            title=template.title.format(**kwargs),
            content=template.content.format(**kwargs),
            level=template.level
        )
    
    def enable_channel(self, channel_type: ChannelType):
        """启用渠道"""
        if channel_type in self.channels:
            self.channels[channel_type].enabled = True
            logger.info(f"Channel {channel_type.value} enabled")
    
    def disable_channel(self, channel_type: ChannelType):
        """禁用渠道"""
        if channel_type in self.channels:
            self.channels[channel_type].enabled = False
            logger.info(f"Channel {channel_type.value} disabled")
    
    def is_channel_enabled(self, channel_type: ChannelType) -> bool:
        """检查渠道是否启用"""
        if channel_type not in self.channels:
            return False
        return self.channels[channel_type].is_enabled()
    
    def get_enabled_channels(self) -> List[ChannelType]:
        """获取所有启用的渠道"""
        return [ct for ct, ch in self.channels.items() if ch.is_enabled()]
    
    async def send(
        self,
        message: Message,
        channels: Optional[List[ChannelType]] = None,
        recipients: Optional[Dict[ChannelType, List[str]]] = None,
    ) -> Dict[ChannelType, bool]:
        """
        发送消息到指定渠道
        
        Args:
            message: 消息对象
            channels: 目标渠道列表，None 表示所有启用渠道
            recipients: 各渠道的接收者映射
        
        Returns:
            Dict[ChannelType, bool]: 各渠道发送结果
        """
        if not self.enabled:
            logger.warning("Notification system is disabled")
            return {}
        
        # 默认发送到所有启用渠道
        if channels is None:
            channels = self.get_enabled_channels()
        
        # 默认接收者
        if recipients is None:
            recipients = {}
        
        results = {}
        
        for channel_type in channels:
            if channel_type not in self.channels:
                logger.warning(f"Channel {channel_type.value} not configured")
                results[channel_type] = False
                continue
            
            channel = self.channels[channel_type]
            if not channel.is_enabled():
                logger.info(f"Channel {channel_type.value} is disabled, skipping")
                results[channel_type] = False
                continue
            
            # 获取该渠道的接收者
            channel_recipients = recipients.get(channel_type, [])
            
            try:
                success = await channel.send(message, channel_recipients)
                results[channel_type] = success
                
                if self.on_send:
                    await self.on_send(channel_type, message, success)
            except Exception as e:
                logger.error(f"Failed to send via {channel_type.value}: {str(e)}")
                results[channel_type] = False
        
        return results
    
    async def send_batch(
        self,
        messages: List[Message],
        channels: Optional[List[ChannelType]] = None,
        recipients: Optional[Dict[ChannelType, List[str]]] = None,
    ) -> Dict[ChannelType, bool]:
        """批量发送消息"""
        if not self.enabled:
            logger.warning("Notification system is disabled")
            return {}
        
        if channels is None:
            channels = self.get_enabled_channels()
        
        if recipients is None:
            recipients = {}
        
        results = {}
        
        for channel_type in channels:
            if channel_type not in self.channels:
                results[channel_type] = False
                continue
            
            channel = self.channels[channel_type]
            if not channel.is_enabled():
                results[channel_type] = False
                continue
            
            channel_recipients = recipients.get(channel_type, [])
            
            try:
                success = await channel.send_batch(messages, channel_recipients)
                results[channel_type] = success
            except Exception as e:
                logger.error(f"Failed to send batch via {channel_type.value}: {str(e)}")
                results[channel_type] = False
        
        return results
    
    async def notify_trade(
        self,
        trade_type: str,
        item_name: str,
        price: float,
        status: str,
        **kwargs
    ):
        """快捷交易通知"""
        message = Message(
            title=f"交易{trade_type}",
            content=f"{item_name} 以 ¥{price:.2f} {status}",
            level="success" if status == "成功" else "warning",
            metadata={
                "item": item_name,
                "price": f"¥{price:.2f}",
                "status": status,
                **kwargs
            }
        )
        
        await self.send(message)
    
    async def notify_price_alert(
        self,
        item_name: str,
        current_price: float,
        target_price: float,
        direction: str
    ):
        """快捷价格提醒"""
        level = "success" if direction == "上涨" else "warning"
        message = Message(
            title=f"价格{direction}提醒",
            content=f"{item_name} 当前价格 ¥{current_price:.2f}，已{direction}至目标价格 ¥{target_price:.2f}",
            level=level,
            metadata={
                "item": item_name,
                "current_price": f"¥{current_price:.2f}",
                "target_price": f"¥{target_price:.2f}",
                "direction": direction
            }
        )
        
        await self.send(message)
    
    async def notify_error(
        self,
        title: str,
        error_message: str,
        **kwargs
    ):
        """快捷错误通知"""
        message = Message(
            title=title,
            content=error_message,
            level="error",
            metadata=kwargs
        )
        
        await self.send(message)
    
    async def health_check(self) -> Dict[ChannelType, bool]:
        """检查所有渠道健康状态"""
        results = {}
        
        for channel_type, channel in self.channels.items():
            if channel.is_enabled():
                results[channel_type] = await channel.health_check()
            else:
                results[channel_type] = False
        
        return results


# 全局通知管理器实例
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """获取全局通知管理器"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def init_notification_manager(config_path: str) -> NotificationManager:
    """初始化通知管理器"""
    global _notification_manager
    _notification_manager = NotificationManager.from_yaml(config_path)
    return _notification_manager
