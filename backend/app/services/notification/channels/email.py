# -*- coding: utf-8 -*-
"""
Email 通知渠道
使用 aiosmtpd 实现异步邮件发送
"""
from typing import List, Optional
import logging
import os

from app.services.notification.channels.base import NotificationChannel, Message

logger = logging.getLogger(__name__)


class EmailChannel(NotificationChannel):
    """Email通知渠道"""
    
    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = 587,
        username: str = None,
        password: str = None,
        use_tls: bool = True,
        from_address: str = None,
        enabled: bool = True
    ):
        super().__init__(enabled)
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "")
        self.smtp_port = smtp_port
        self.username = username or os.getenv("SMTP_USERNAME", "")
        self.password = password or os.getenv("SMTP_PASSWORD", "")
        self.use_tls = use_tls
        self.from_address = from_address or os.getenv("SMTP_FROM", "noreply@cs2trade.com")
    
    def _build_html(self, message: Message) -> str:
        """构建HTML邮件内容"""
        level_colors = {
            "info": "#3498db",
            "success": "#27ae60", 
            "warning": "#f39c12",
            "error": "#e74c3c"
        }
        color = level_colors.get(message.level.value, "#3498db")
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px;">
                <div style="background: {color}; color: white; padding: 15px 20px; border-radius: 8px 8px 0 0;">
                    <h2 style="margin: 0;">{message.title}</h2>
                </div>
                <div style="padding: 20px;">
                    <p>{message.content}</p>
                    {self._build_data_html(message.data) if message.data else ""}
                </div>
                <div style="background: #f5f5f5; padding: 10px 20px; border-radius: 0 0 8px 8px; font-size: 12px; color: #666;">
                    <p style="margin: 0;">CS2 Smart Trader - 自动发送</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _build_data_html(self, data: dict) -> str:
        """构建数据部分的HTML"""
        if not data:
            return ""
        
        rows = ""
        for key, value in data.items():
            rows += f"<tr><td style='padding: 5px 10px; border-bottom: 1px solid #eee;'><strong>{key}</strong></td><td style='padding: 5px 10px; border-bottom: 1px solid #eee;'>{value}</td></tr>"
        
        return f"<table style='width: 100%; border-collapse: collapse; margin-top: 10px;'>{rows}</table>"
    
    async def send(self, message: Message) -> bool:
        """发送邮件"""
        if not self.enabled:
            logger.info("Email channel is disabled, skipping")
            return False
        
        if not self.smtp_host:
            logger.warning("Email SMTP not configured, skipping notification")
            return False
        
        try:
            recipients = message.recipients or []
            if not recipients:
                logger.warning("No recipients specified for email")
                return False
            
            # 异步发送邮件
            import asyncio
            from aiosmtplib import send
            from email.message import EmailMessage
            
            msg = EmailMessage()
            msg["Subject"] = message.title
            msg["From"] = self.from_address
            msg["To"] = ", ".join(recipients)
            msg.set_content(message.content)
            msg.add_alternative(self._build_html(message), subtype="html")
            
            await send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls
            )
            
            logger.info(f"Email sent to {recipients}: {message.title}")
            return True
            
        except ImportError:
            logger.warning("aiosmtplib not installed, email notifications disabled")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def send_batch(self, messages: List[Message]) -> bool:
        """批量发送邮件"""
        if not self.enabled:
            return False
        
        results = []
        for msg in messages:
            result = await self.send(msg)
            results.append(result)
        
        return any(results)  # 至少发送成功一封
    
    async def health_check(self) -> bool:
        """检查SMTP配置"""
        if not self.enabled:
            return False
        return bool(self.smtp_host and self.username)
