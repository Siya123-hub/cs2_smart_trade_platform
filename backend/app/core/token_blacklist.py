# -*- coding: utf-8 -*-
"""
Token 黑名单管理
使用 Redis 存储 token 黑名单
"""
from typing import Optional
import redis.asyncio as redis
from datetime import datetime, timedelta

from app.core.config import settings


class TokenBlacklist:
    """Token 黑名单管理器"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def get_client(self) -> redis.Redis:
        """获取 Redis 客户端"""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client
    
    async def add(self, token: str, expires_in: int = 86400) -> bool:
        """
        将 token 加入黑名单
        
        Args:
            token: JWT token
            expires_in: 过期时间（秒），默认 24 小时
        
        Returns:
            是否成功
        """
        try:
            client = await self.get_client()
            # 从 token 中获取过期时间
            from app.core.security import decode_token
            payload = decode_token(token)
            
            if payload:
                exp = payload.get("exp")
                if exp:
                    # 计算剩余有效时间
                    exp_datetime = datetime.fromtimestamp(exp)
                    remaining = (exp_datetime - datetime.utcnow()).total_seconds()
                    if remaining > 0:
                        await client.setex(
                            f"blacklist:{token}",
                            int(remaining),
                            "1"
                        )
                        return True
            
            # 如果无法解析，默认 24 小时
            await client.setex(f"blacklist:{token}", expires_in, "1")
            return True
            
        except Exception as e:
            print(f"Error adding token to blacklist: {e}")
            return False
    
    async def is_blacklisted(self, token: str) -> bool:
        """
        检查 token 是否在黑名单中
        
        Args:
            token: JWT token
        
        Returns:
            是否在黑名单中
        """
        try:
            client = await self.get_client()
            result = await client.get(f"blacklist:{token}")
            return result is not None
        except Exception:
            return False
    
    async def remove(self, token: str) -> bool:
        """
        从黑名单中移除 token
        
        Args:
            token: JWT token
        
        Returns:
            是否成功
        """
        try:
            client = await self.get_client()
            await client.delete(f"blacklist:{token}")
            return True
        except Exception:
            return False
    
    async def close(self):
        """关闭 Redis 连接"""
        if self.redis_client:
            await self.redis_client.close()


# 全局黑名单实例
token_blacklist = TokenBlacklist()


async def add_token_to_blacklist(token: str) -> bool:
    """将 token 加入黑名单"""
    return await token_blacklist.add(token)


async def check_token_blacklist(token: str) -> bool:
    """检查 token 是否在黑名单"""
    return await token_blacklist.is_blacklisted(token)
