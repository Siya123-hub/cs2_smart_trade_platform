# -*- coding: utf-8 -*-
"""
通知渠道模块
支持多渠道通知: WebSocket, Email, Slack, Discord, Telegram
"""
from app.services.notification.channels.base import NotificationChannel, Message, MessageLevel
from app.services.notification.channels.websocket import WebSocketChannel
from app.services.notification.channels.email import EmailChannel
from app.services.notification.channels.slack import SlackChannel
from app.services.notification.channels.discord import DiscordChannel
from app.services.notification.channels.telegram import TelegramChannel
from app.services.notification.channels.manager import NotificationManager

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
