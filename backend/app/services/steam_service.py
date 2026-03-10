# -*- coding: utf-8 -*-
"""
Steam API 服务
"""
import asyncio
import logging
from typing import Optional, Dict, List, Any

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
        self.session = aiohttp.ClientSession(timeout=timeout or self.DEFAULT_TIMEOUT)
    
    async def close(self):
        """关闭会话"""
        await self.session.close()
    
    async def cleanup(self):
        """清理资源"""
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
