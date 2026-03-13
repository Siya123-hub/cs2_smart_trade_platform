# -*- coding: utf-8 -*-
"""
通知渠道基类
定义通知渠道的统一接口
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class MessageLevel(str, Enum):
    """消息级别"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Message(BaseModel):
    """通知消息"""
    title: str
    content: str
    level: MessageLevel = MessageLevel.INFO
    data: Optional[Dict[str, Any]] = None
    recipients: Optional[List[str]] = None


class NotificationChannel(ABC):
    """通知渠道抽象基类"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    @abstractmethod
    async def send(self, message: Message) -> bool:
        """
        发送单条消息
        
        Args:
            message: 消息对象
            
        Returns:
            是否发送成功
        """
        pass
    
    @abstractmethod
    async def send_batch(self, messages: List[Message]) -> bool:
        """
        批量发送消息
        
        Args:
            messages: 消息列表
            
        Returns:
            是否发送成功
        """
        pass
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            渠道是否可用
        """
        return self.enabled
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(enabled={self.enabled})"
