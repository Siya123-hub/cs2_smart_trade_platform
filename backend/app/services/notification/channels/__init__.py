# -*- coding: utf-8 -*-
"""
通知渠道包
"""
from .base import NotificationChannel, Message, MessageLevel
from .websocket import WebSocketChannel
from .email import EmailChannel
from .slack import SlackChannel
from .discord import DiscordChannel
from .telegram import TelegramChannel
from .manager import NotificationManager

__all__ = [
    "NotificationChannel",
    "Message",
    "MessageLevel",
    "WebSocketChannel",
    "EmailChannel",
    "SlackChannel",
    "DiscordChannel",
    "TelegramChannel",
    "NotificationManager"
]
