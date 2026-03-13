# -*- coding: utf-8 -*-
"""
邮件通知渠道
支持SMTP发送交易通知
"""
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List, Optional
from pydantic import BaseModel, Field
import logging

from app.services.notification.base import NotificationChannel, Message, ChannelConfig

logger = logging.getLogger(__name__)


class EmailConfig(ChannelConfig):
    """邮件通知配置"""
    enabled: bool = Field(default=False)
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP服务器地址")
    smtp_port: int = Field(default=587, description="SMTP端口")
    smtp_username: str = Field(default="", description="SMTP用户名")
    smtp_password: str = Field(default="", description="SMTP密码")
    use_tls: bool = Field(default=True, description="是否使用TLS")
    from_name: str = Field(default="CS2 Trader", description="发件人名称")
    from_email: str = Field(default="noreply@example.com", description="发件人邮箱")
    recipients: List[str] = Field(default_factory=list, description="默认收件人列表")


class EmailNotification(NotificationChannel):
    """邮件通知渠道"""
    
    def __init__(self, config: EmailConfig):
        super().__init__(config)
        self.smtp_host = config.smtp_host
        self.smtp_port = config.smtp_port
        self.smtp_username = config.smtp_username
        self.smtp_password = config.smtp_password
        self.use_tls = config.use_tls
        self.from_name = config.from_name
        self.from_email = config.from_email
        self.default_recipients = config.recipients
    
    def _create_message(self, message: Message, recipient: str) -> MIMEMultipart:
        """创建邮件消息"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(message.title, 'utf-8')
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = recipient
        
        # Plain text版本
        text_content = f"{message.title}\n\n{message.content}"
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        
        # HTML版本
        html_content = self._create_html_content(message)
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        return msg
    
    def _create_html_content(self, message: Message) -> str:
        """创建HTML内容"""
        level_colors = {
            "info": "#3498db",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "success": "#27ae60",
        }
        color = level_colors.get(message.level, "#3498db")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #999; font-size: 12px; }}
                .level-badge {{ display: inline-block; padding: 5px 10px; background-color: {color}; color: white; border-radius: 3px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin: 0;">{message.title}</h2>
                </div>
                <div class="content">
                    <p>{message.content}</p>
                    <p style="margin-top: 20px;">
                        <span class="level-badge">{message.level.upper()}</span>
                    </p>
                </div>
                <div class="footer">
                    <p>CS2 智能交易平台</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    async def _send_sync(self, msg: MIMEMultipart, recipient: str) -> bool:
        """同步发送邮件（在线程池中运行）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_sync_internal, msg, recipient)
    
    def _send_sync_internal(self, msg: MIMEMultipart, recipient: str) -> bool:
        """内部同步发送方法"""
        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            self._logger.info(f"Email sent successfully to {recipient}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to send email to {recipient}: {str(e)}")
            return False
    
    async def send(self, message: Message, recipients: List[str]) -> bool:
        """发送单条邮件"""
        if not self.enabled:
            self._logger.warning("Email notification is disabled")
            return False
        
        target_recipients = recipients if recipients else self.default_recipients
        if not target_recipients:
            self._logger.error("No recipients specified")
            return False
        
        success = True
        for recipient in target_recipients:
            msg = self._create_message(message, recipient)
            result = await self._send_sync(msg, recipient)
            if not result:
                success = False
        
        return success
    
    async def send_batch(self, messages: List[Message], recipients: List[str]) -> bool:
        """批量发送邮件"""
        if not self.enabled:
            self._logger.warning("Email notification is disabled")
            return False
        
        target_recipients = recipients if recipients else self.default_recipients
        if not target_recipients:
            self._logger.error("No recipients specified")
            return False
        
        success = True
        for message in messages:
            result = await self.send(message, target_recipients)
            if not result:
                success = False
            # 添加小延迟避免SMTP限流
            await asyncio.sleep(0.1)
        
        return success
    
    async def health_check(self) -> bool:
        """健康检查"""
        if not self.enabled:
            return False
        
        # 简单检查SMTP配置是否完整
        if not self.smtp_host or not self.smtp_username:
            return False
        
        return True
