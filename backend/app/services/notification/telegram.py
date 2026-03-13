# -*- coding: utf-8 -*-
"""
Telegram 通知渠道
支持 Bot API 发送
"""
import aiohttp
import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import json

from app.services.notification.base import NotificationChannel, Message, ChannelConfig

logger = logging.getLogger(__name__)


class TelegramConfig(ChannelConfig):
    """Telegram 通知配置"""
    enabled: bool = Field(default=False)
    bot_token: str = Field(default="", description="Telegram Bot Token")
    chat_ids: List[str] = Field(default_factory=list, description="默认聊天ID列表")
    parse_mode: str = Field(default="Markdown", description="解析模式: Markdown 或 HTML")


class TelegramNotification(NotificationChannel):
    """Telegram 通知渠道"""
    
    def __init__(self, config: TelegramConfig):
        super().__init__(config)
        self.bot_token = config.bot_token
        self.default_chat_ids = config.chat_ids
        self.parse_mode = config.parse_mode
        self.api_base_url = f"https://api.telegram.org/bot{config.bot_token}"
    
    def _get_level_emoji(self, level: str) -> str:
        """获取级别对应的emoji"""
        emojis = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
        }
        return emojis.get(level, "ℹ️")
    
    def _format_text_markdown(self, message: Message) -> str:
        """Markdown 格式文本"""
        emoji = self._get_level_emoji(message.level)
        text = f"{emoji} *{message.title}*\n\n{message.content}"
        
        # 添加元数据
        if message.metadata:
            text += "\n\n"
            for key, value in message.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    text += f"_{key}:_ `{value}`\n"
        
        # 添加 footer
        text += f"\n\n---\n_CSto 智能交易平台_"
        
        return text
    
    def _format_text_html(self, message: Message) -> str:
        """HTML 格式文本"""
        emoji = self._get_level_emoji(message.level)
        level_colors = {
            "info": "#3498db",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "success": "#27ae60",
        }
        color = level_colors.get(message.level, "#3498db")
        
        text = f"{emoji} <b>{message.title}</b>\n\n{message.content}"
        
        # 添加元数据
        if message.metadata:
            text += "\n\n"
            for key, value in message.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    text += f"<i>{key}:</i> <code>{value}</code>\n"
        
        # 添加 footer
        text += f"\n\n---\n<i>CS2 智能交易平台</i>"
        
        return text
    
    def _format_text(self, message: Message) -> str:
        """格式化文本"""
        if self.parse_mode == "HTML":
            return self._format_text_html(message)
        else:
            return self._format_text_markdown(message)
    
    async def _send_message(self, chat_id: str, text: str, disable_notification: bool = False) -> bool:
        """发送消息到 Telegram"""
        if not self.bot_token:
            self._logger.error("Bot token not configured")
            return False
        
        url = f"{self.api_base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": self.parse_mode if self.parse_mode in ["Markdown", "HTML"] else "Markdown",
            "disable_notification": disable_notification
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            self._logger.info(f"Telegram message sent to {chat_id}")
                            return True
                        else:
                            self._logger.error(f"Telegram API error: {result}")
                            return False
                    else:
                        response_text = await response.text()
                        self._logger.error(f"Telegram request failed: {response.status} - {response_text}")
                        return False
        except asyncio.TimeoutError:
            self._logger.error("Telegram request timed out")
            return False
        except Exception as e:
            self._logger.error(f"Failed to send Telegram message: {str(e)}")
            return False
    
    async def _send_to_chats(self, message: Message, chat_ids: List[str], disable_notification: bool = False) -> bool:
        """发送消息到多个聊天"""
        success = True
        for chat_id in chat_ids:
            text = self._format_text(message)
            result = await self._send_message(chat_id, text, disable_notification)
            if not result:
                success = False
            # 添加小延迟避免限流
            await asyncio.sleep(0.1)
        return success
    
    async def send(self, message: Message, recipients: List[str]) -> bool:
        """发送单条 Telegram 消息"""
        if not self.enabled:
            self._logger.warning("Telegram notification is disabled")
            return False
        
        if not self.bot_token:
            self._logger.error("Bot token not configured")
            return False
        
        # recipients 在 Telegram 中是 chat_ids
        target_chat_ids = recipients if recipients else self.default_chat_ids
        if not target_chat_ids:
            self._logger.error("No chat IDs specified")
            return False
        
        return await self._send_to_chats(message, target_chat_ids)
    
    async def send_batch(self, messages: List[Message], recipients: List[str]) -> bool:
        """批量发送 Telegram 消息"""
        if not self.enabled:
            self._logger.warning("Telegram notification is disabled")
            return False
        
        if not self.bot_token:
            self._logger.error("Bot token not configured")
            return False
        
        target_chat_ids = recipients if recipients else self.default_chat_ids
        if not target_chat_ids:
            self._logger.error("No chat IDs specified")
            return False
        
        success = True
        for message in messages:
            result = await self._send_to_chats(message, target_chat_ids)
            if not result:
                success = False
        
        return success
    
    async def health_check(self) -> bool:
        """健康检查"""
        if not self.enabled:
            return False
        
        if not self.bot_token:
            return False
        
        # 尝试获取 bot 信息
        url = f"{self.api_base_url}/getMe"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            self._logger.info(f"Telegram bot connected: {result.get('result', {}).get('username')}")
                            return True
        except Exception as e:
            self._logger.error(f"Telegram health check failed: {str(e)}")
            return False
        
        return False
