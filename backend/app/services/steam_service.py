# -*- coding: utf-8 -*-
"""
Steam API 服务
"""
import asyncio
import logging
from typing import Optional, Dict, List, Any, Set
from contextlib import asynccontextmanager

import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


class SteamAPI:
    """Steam API 客户端"""
    
    # 默认超时配置
    DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10)
    
    def __init__(self, api_key: Optional[str] = None, timeout: Optional[aiohttp.ClientTimeout] = None):
        self.api_key = api_key or settings.STEAM_API_KEY
        self.base_url = "https://api.steampowered.com"
        self.market_url = "https://steamcommunity.com/market"
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def health_check(self) -> bool:
        """
        检查 Session 健康状态
        
        Returns:
            是否健康
        """
        if self._session is None:
            return False
        
        # 检查 session 是否已关闭
        if self._session.closed:
            return False
        
        # 尝试发送一个轻量级请求来验证连接
        try:
            # 使用一个简单且快速的 API 端点来检查连接
            test_url = f"{self.base_url}/ISteamUser/GetPlayerSummaries/v0002/"
            params = {"key": self.api_key, "steamids": "76561197960435530"}  # 一个测试ID
            
            async with self._session.get(
                test_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                # 检查响应状态码是否合理
                return response.status in (200, 400, 401)  # 400/401 表示API有效但参数问题，session本身是健康的
        except asyncio.TimeoutError:
            logger.warning("Steam API 健康检查超时")
            return False
        except aiohttp.ClientError as e:
            logger.warning(f"Steam API 健康检查失败: {e}")
            return False
        except Exception as e:
            logger.warning(f"Steam API 健康检查异常: {e}")
            return False
    
    async def ensure_healthy_session(self):
        """
        确保 Session 处于健康状态，必要时重新创建
        """
        if not await self.health_check():
            logger.info("Steam API Session 不健康，重新创建...")
            await self.close()
            # 重新创建 session
            self._session = aiohttp.ClientSession(timeout=self.DEFAULT_TIMEOUT)
    
    @property
    def session(self) -> aiohttp.ClientSession:
        """获取或创建 session（延迟初始化）"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.DEFAULT_TIMEOUT)
        return self._session
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def cleanup(self):
        """清理资源"""
        await self.close()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def _request(
        self,
        url: str,
        params: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """发送请求"""
        headers = kwargs.pop("headers", {})
        headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        
        timeout = kwargs.pop("timeout", None)
        
        try:
            async with self.session.get(
                url, 
                params=params, 
                headers=headers, 
                timeout=timeout or self.DEFAULT_TIMEOUT,
                **kwargs
            ) as response:
                if response.status != 200:
                    logger.error(f"Steam API Error: {response.status}")
                    raise Exception(f"Steam API Error: {response.status}")
                
                return await response.json()
        except asyncio.TimeoutError:
            logger.error(f"Steam API 请求超时: {url}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Steam API 连接错误: {e}")
            raise
    
    async def get_player_summaries(self, steam_ids: List[str]) -> List[Dict[str, Any]]:
        """获取玩家基本信息"""
        if not self.api_key:
            raise Exception("需要 Steam API Key")
        
        params = {
            "key": self.api_key,
            "steamids": ",".join(steam_ids),
        }
        
        url = f"{self.base_url}/ISteamUser/GetPlayerSummaries/v0002/"
        data = await self._request(url, params=params)
        
        return data.get("response", {}).get("players", [])
    
    async def get_price_overview(
        self,
        market_hash_name: str,
        app_id: int = 730,
        currency: int = 1  # 1=USD, 2=GBP, 3=...
    ) -> Optional[Dict[str, Any]]:
        """获取市场价格概览"""
        params = {
            "appid": app_id,
            "market_hash_name": market_hash_name,
            "currency": currency,
        }
        
        url = f"{self.market_url}/priceoverview/"
        
        try:
            data = await self._request(url, params=params)
            return data
        except Exception as e:
            logger.warning(f"获取价格概览失败: {market_hash_name}, 错误: {e}")
            return None
    
    async def get_listings(
        self,
        market_hash_name: str,
        app_id: int = 730,
        start: int = 0,
        count: int = 10
    ) -> Optional[Dict[str, Any]]:
        """获取市场挂单"""
        params = {
            "appid": app_id,
            "market_hash_name": market_hash_name,
            "start": start,
            "count": count,
        }
        
        url = f"{self.market_url}/itemorders/"
        
        try:
            data = await self._request(url, params=params)
            return data
        except Exception as e:
            logger.warning(f"获取市场挂单失败: {market_hash_name}, 错误: {e}")
            return None
    
    async def get_price_histogram(
        self,
        market_hash_name: str,
        app_id: int = 730,
        currency: int = 1
    ) -> Optional[Dict[str, Any]]:
        """获取价格直方图 (历史数据)"""
        params = {
            "appid": app_id,
            "market_hash_name": market_hash_name,
            "currency": currency,
        }
        
        url = f"{self.market_url}/pricehistogram/"
        
        try:
            data = await self._request(url, params=params)
            return data
        except Exception as e:
            logger.warning(f"获取价格直方图失败: {market_hash_name}, 错误: {e}")
            return None


class SteamTrade:
    """Steam 交易服务 (基于 SteamKit2 概念的实现)"""
    
    def __init__(
        self,
        steam_id: str,
        session_token: str,
        ma_file: Optional[Dict] = None
    ):
        self.steam_id = steam_id
        self.session_token = session_token
        self.ma_file = ma_file
        self.is_logged_in = False
    
    async def login(self) -> bool:
        """登录 Steam"""
        # 这里需要实现 SteamKit2 的登录逻辑
        # 实际实现需要使用 steamkit2 库
        self.is_logged_in = True
        return True
    
    async def get_inventory(
        self,
        app_id: int = 730,
        context_id: int = 2
    ) -> List[Dict[str, Any]]:
        """获取库存"""
        if not self.is_logged_in:
            raise Exception("未登录 Steam")
        
        # 实际实现需要调用 Steam API
        return []
    
    async def get_trade_offers(
        self,
        get_received: bool = True,
        get_sent: bool = False
    ) -> List[Dict[str, Any]]:
        """获取交易报价"""
        if not self.is_logged_in:
            raise Exception("未登录 Steam")
        
        # 实际实现需要调用 Steam API
        return []
    
    async def create_trade_offer(
        self,
        partner_steam_id: str,
        items_to_give: List[Dict] = None,
        items_to_receive: List[Dict] = None,
        message: str = ""
    ) -> Optional[str]:
        """创建交易报价"""
        if not self.is_logged_in:
            raise Exception("未登录 Steam")
        
        # 实际实现需要调用 Steam API
        return None
    
    async def accept_trade_offer(self, trade_offer_id: str) -> bool:
        """接受交易报价"""
        if not self.is_logged_in:
            raise Exception("未登录 Steam")
        
        # 实际实现需要调用 Steam API
        return True
    
    async def decline_trade_offer(self, trade_offer_id: str) -> bool:
        """拒绝交易报价"""
        if not self.is_logged_in:
            raise Exception("未登录 Steam")
        
        # 实际实现需要调用 Steam API
        return True


# 全局 API 实例
_steam_api: Optional[SteamAPI] = None


def get_steam_api() -> SteamAPI:
    """获取 Steam API 实例"""
    global _steam_api
    if _steam_api is None:
        _steam_api = SteamAPI()
    return _steam_api


# 别名兼容
SteamService = SteamAPI
