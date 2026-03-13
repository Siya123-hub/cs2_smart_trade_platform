# -*- coding: utf-8 -*-
"""
Telegram 通知渠道
使用 Bot API 实现消息推送
"""
from typing import List, Optional
import logging
import os

from app.services.notification.channels.base import NotificationChannel, Message

logger = logging.getLogger(__name__)


class TelegramChannel(NotificationChannel):
    """Telegram通知渠道"""
    
    def __init__(
        self,
        bot_token: str = None,
        chat_ids: List[str] = None,
        enabled: bool = True
    ):
        super().__init__(enabled)
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_ids = chat_ids or os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
        self.chat_ids = [cid.strip() for cid in self.chat_ids if cid.strip()]
    
    def _build_message(self, message: Message) -> str:
        """构建Telegram消息"""
        level_emoji = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        emoji = level_emoji.get(message.level.value, "ℹ️")
        
        text = f"{emoji} *{message.title}*\n\n{message.content}"
        
        if message.data:
            text += "\n\n"
            for key, value in message.data.items():
                if isinstance(value, (str, int, float, bool)):
                    text += f"• *{key}*: `{value}`\n"
        
        return text
    
    async def send(self, message: Message) -> bool:
        """发送Telegram消息"""
        if not self.enabled:
            return False
        
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return False
        
        recipients = message.recipients or self.chat_ids
        if not recipients:
            logger.warning("No chat IDs specified for Telegram")
            return False
        
        try:
            import aiohttp
            
            text = self._build_message(message)
            results = []
            
            async with aiohttp.ClientSession() as session:
                for chat_id in recipients:
                    url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "Markdown"
                    }
                    
                    async with session.post(url, json=payload) as resp:
                        if resp.status == 200:
                            results.append(True)
                        else:
                            logger.error(f"Telegram API error: {resp.status}")
                            results.append(False)
            
            success = any(results)
            if success:
                logger.info(f"Telegram notification sent: {message.title}")
            return success
                        
        except ImportError:
            logger.warning("aiohttp not installed, Telegram notifications disabled")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    async def send_batch(self, messages: List[Message]) -> bool:
        """批量发送Telegram消息"""
        if not self.enabled:
            return False
        
        results = []
        for msg in messages:
            result = await self.send(msg)
            results.append(result)
        
        return any(results)
    
    async def health_check(self) -> bool:
        """检查Telegram配置"""
        if not self.enabled:
            return False
        return bool(self.bot_token and self.chat_ids)
