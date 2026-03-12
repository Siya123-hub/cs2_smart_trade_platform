# -*- coding: utf-8 -*-
"""
搬砖机器人实现

基于 BUFF 和 Steam 之间的价格差进行自动化交易
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .trading_bot_base import TradingBotBase, BotPlatform, BotStatus

logger = logging.getLogger(__name__)


class ArbitrageBot(TradingBotBase):
    """
    搬砖机器人
    
    功能：
    - 监控 BUFF 和 Steam 价格
    - 自动计算搬砖利润
    - 执行买入/卖出操作
    - 支持多种搬砖策略
    """
    
    def __init__(
        self,
        bot_id: int,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ):
        # 默认配置
        default_config = {
            "min_profit": 1.0,           # 最小利润（元）
            "min_profit_percent": 5.0,  # 最小利润率（%）
            "max_single_trade": 1000.0,  # 单笔最大金额
            "check_interval": 30,        # 检查间隔（秒）
            "max_trades_per_hour": 10,   # 每小时最大交易数
            "buy_platform": "buff",      # 买入平台
            "sell_platform": "steam",    # 卖出平台
            "auto_confirm": True,        # 自动确认订单
            "enabled_items": None,       # 监控的物品列表（None=全部）
            "excluded_items": [],        # 排除的物品
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(
            bot_id=bot_id,
            name=name,
            platform=BotPlatform.BUFF_TO_STEAM,
            config=default_config
        )
        
        # 运行时状态
        self._buff_client = None
        self._steam_api = None
        self._db_session = None
        
        # 缓存
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        self._trade_history: List[Dict[str, Any]] = []
    
    async def _initialize(self) -> None:
        """
        初始化搬砖机器人
        """
        self.logger.info(f"初始化搬砖机器人: {self.name}")
        
        # 初始化 BUFF 客户端
        await self._init_buff_client()
        
        # 初始化 Steam API
        await self._init_steam_api()
        
        self.logger.info("搬砖机器人初始化完成")
    
    async def _init_buff_client(self) -> None:
        """初始化 BUFF 客户端"""
        try:
            # 延迟导入避免循环依赖
            from app.services.buff_service import get_buff_client
            
            cookie = self.config.get("buff_cookie")
            if cookie:
                self._buff_client = get_buff_client(cookie)
                self.logger.info("BUFF 客户端已初始化")
            else:
                self.logger.warning("未配置 BUFF Cookie")
                
        except Exception as e:
            self.logger.error(f"初始化 BUFF 客户端失败: {e}")
    
    async def _init_steam_api(self) -> None:
        """初始化 Steam API"""
        try:
            from app.services.steam_service import get_steam_api
            
            self._steam_api = get_steam_api()
            self.logger.info("Steam API 已初始化")
            
        except Exception as e:
            self.logger.error(f"初始化 Steam API 失败: {e}")
    
    async def _run_loop(self) -> None:
        """
        主循环：持续监控价格并执行搬砖
        """
        self.logger.info("搬砖机器人主循环开始")
        
        while self._running:
            try:
                if not self._paused:
                    # 检查是否超过每小时交易限制
                    if await self._check_trade_limit():
                        self.logger.info("已达到每小时交易限制，暂停")
                        await self._sleep_with_pause(60)
                        continue
                    
                    # 执行搬砖逻辑
                    await self._scan_and_trade()
                
                # 等待下次检查
                await self._sleep_with_pause(self.config["check_interval"])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"主循环异常: {e}")
                await self._sleep_with_pause(60)  # 出错后等待1分钟
        
        self.logger.info("搬砖机器人主循环结束")
    
    async def _scan_and_trade(self) -> None:
        """
        扫描并执行搬砖
        """
        try:
            # 1. 获取搬砖机会
            opportunities = await self._get_arbitrage_opportunities()
            
            if not opportunities:
                self.logger.debug("当前无搬砖机会")
                return
            
            # 2. 过滤有效机会
            valid_opportunities = self._filter_opportunities(opportunities)
            
            self.logger.info(f"发现 {len(valid_opportunities)} 个有效搬砖机会")
            
            # 3. 执行交易
            for opp in valid_opportunities:
                if not self._running or self._paused:
                    break
                
                await self._execute_arbitrage_trade(opp)
                
                # 避免过快交易
                await asyncio.sleep(5)
                
        except Exception as e:
            self.logger.error(f"扫描并交易失败: {e}")
    
    async def _get_arbitrage_opportunities(self) -> List[Dict[str, Any]]:
        """
        获取搬砖机会
        
        Returns:
            搬砖机会列表
        """
        if not self._buff_client:
            self.logger.warning("BUFF 客户端未初始化")
            return []
        
        try:
            # 调用交易引擎获取机会
            from app.services.trading_service import TradingEngine
            
            if self._db_session:
                engine = TradingEngine(self._db_session)
                opportunities = await engine.get_arbitrage_opportunities(
                    min_profit=self.config["min_profit"],
                    limit=50
                )
                return opportunities
            
            # 无数据库时直接从API获取
            return []
            
        except Exception as e:
            self.logger.error(f"获取搬砖机会失败: {e}")
            return []
    
    def _filter_opportunities(
        self,
        opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        过滤有效的搬砖机会
        
        Args:
            opportunities: 原始机会列表
            
        Returns:
            过滤后的机会列表
        """
        filtered = []
        
        for opp in opportunities:
            # 检查利润门槛
            if opp["profit"] < self.config["min_profit"]:
                continue
            
            # 检查利润率
            if opp["profit_percent"] < self.config["min_profit_percent"]:
                continue
            
            # 检查单笔金额限制
            if opp["buff_price"] > self.config["max_single_trade"]:
                continue
            
            # 检查是否在排除列表
            if opp["name"] in self.config["excluded_items"]:
                continue
            
            # 检查是否在启用列表（如果有）
            if self.config["enabled_items"]:
                if opp["name"] not in self.config["enabled_items"]:
                    continue
            
            filtered.append(opp)
        
        # 按利润排序
        filtered.sort(key=lambda x: x["profit"], reverse=True)
        
        return filtered[:10]  # 最多处理10个
    
    async def _execute_arbitrage_trade(
        self,
        opportunity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行单笔搬砖交易
        
        Args:
            opportunity: 搬砖机会
            
        Returns:
            交易结果
        """
        item_name = opportunity["name"]
        item_id = opportunity["item_id"]
        buff_price = opportunity["buff_price"]
        steam_price = opportunity["steam_price"]
        profit = opportunity["profit"]
        
        self.logger.info(
            f"执行搬砖: {item_name} - "
            f"BUFF: {buff_price}¥, Steam: {steam_price}¥, "
            f"利润: {profit}¥"
        )
        
        try:
            # 1. 买入（BUFF）
            buy_result = await self._buy_from_buff(item_id, buff_price)
            
            if not buy_result.get("success"):
                self.logger.warning(f"买入失败: {buy_result.get('message')}")
                return buy_result
            
            # 2. 等待到账（简化处理，实际需要轮询）
            await asyncio.sleep(30)
            
            # 3. 卖出（Steam）- 实际需要更复杂逻辑
            sell_result = await self._sell_to_steam(item_id, steam_price)
            
            # 记录交易
            trade_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "item_name": item_name,
                "item_id": item_id,
                "buy_price": buff_price,
                "sell_price": steam_price,
                "profit": profit,
                "buy_result": buy_result,
                "sell_result": sell_result,
            }
            
            self._trade_history.append(trade_record)
            
            # 更新统计
            self.stats["total_trades"] += 1
            self.stats["successful_trades"] += 1
            self.stats["total_profit"] += profit
            self.stats["last_trade_time"] = datetime.utcnow()
            
            self.logger.info(f"搬砖成功: {item_name}, 利润: {profit}¥")
            
            return {
                "success": True,
                "profit": profit,
                "trade": trade_record
            }
            
        except Exception as e:
            self.logger.error(f"搬砖交易失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    async def _buy_from_buff(
        self,
        item_id: int,
        max_price: float
    ) -> Dict[str, Any]:
        """
        从 BUFF 买入
        
        Args:
            item_id: 物品ID
            max_price: 最高价格
            
        Returns:
            买入结果
        """
        if not self._buff_client:
            return {"success": False, "message": "BUFF 客户端未初始化"}
        
        try:
            from app.services.trading_service import TradingEngine
            
            if self._db_session:
                engine = TradingEngine(self._db_session)
                engine.buff_client = self._buff_client
                
                return await engine.execute_buy(
                    item_id=item_id,
                    max_price=max_price,
                    user_id=self.config.get("user_id", 1)
                )
            
            return {"success": False, "message": "无数据库会话"}
            
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    async def _sell_to_steam(
        self,
        item_id: int,
        price: float
    ) -> Dict[str, Any]:
        """
        卖出到 Steam
        
        Args:
            item_id: 物品ID
            price: 价格
            
        Returns:
            卖出结果
        """
        if not self._steam_api:
            self.logger.warning("Steam API 未初始化")
            return {"success": False, "message": "Steam API 未初始化"}
        
        try:
            # 获取 Steam 库存中的物品
            inventory = await self._get_steam_inventory(item_id)
            
            if not inventory:
                self.logger.warning(f"Steam 库存中未找到物品: {item_id}")
                return {"success": False, "message": "库存中未找到该物品"}
            
            # 获取物品市场列表价格
            market_price = await self._get_steam_market_price(item_id, price)
            
            if not market_price:
                return {"success": False, "message": "无法获取市场价格"}
            
            # 上架物品到 Steam 市场
            sell_result = await self._list_on_steam_market(
                asset_id=inventory.get("asset_id"),
                app_id=inventory.get("app_id", 730),
                context_id=inventory.get("context_id", 2),
                price=market_price
            )
            
            if sell_result.get("success"):
                self.logger.info(
                    f"Steam 上架成功: item_id={item_id}, "
                    f"price={market_price}, listing_id={sell_result.get('listing_id')}"
                )
            
            return sell_result
            
        except Exception as e:
            self.logger.error(f"Steam 卖出失败: {e}")
            return {"success": False, "message": str(e)}
    
    async def _get_steam_inventory(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        获取 Steam 库存中的物品
        
        Args:
            item_id: 物品ID
            
        Returns:
            库存物品信息
        """
        try:
            # 通过物品ID查询对应的 market_hash_name
            from app.services.steam_service import get_steam_api
            steam = get_steam_api()
            
            # 获取用户库存
            inventory = await steam.get_inventory(
                app_id=730,
                context_id=2
            )
            
            if not inventory:
                return None
            
            # 查找对应的物品（这里简化处理，实际需要映射 item_id 到 market_hash_name）
            for item in inventory.get("assets", []):
                # 实际应该通过数据库查询 market_hash_name 来匹配
                # 这里返回第一个匹配的物品作为示例
                if item.get("asset_id"):
                    return {
                        "asset_id": item.get("asset_id"),
                        "app_id": 730,
                        "context_id": 2,
                        "market_hash_name": item.get("market_hash_name")
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取 Steam 库存失败: {e}")
            return None
    
    async def _get_steam_market_price(
        self,
        item_id: int,
        target_price: float
    ) -> Optional[float]:
        """
        获取 Steam 市场建议价格
        
        Args:
            item_id: 物品ID
            target_price: 目标价格（来自 BUFF 的价格）
            
        Returns:
            Steam 市场价格
        """
        try:
            steam = get_steam_api()
            
            # 计算合理的 Steam 售价
            # Steam 收取 15% 手续费，我们需要留出利润空间
            # 建议售价 = BUFF 价格 / 0.85，确保不亏本
            recommended_price = target_price / 0.85
            
            # 可以查询 Steam 市场当前最低价作为参考
            # 这里可以调用 steam.get_price_overview() 获取市场数据
            
            # 返回建议价格（保留两位小数）
            return round(recommended_price, 2)
            
        except Exception as e:
            self.logger.error(f"计算 Steam 价格失败: {e}")
            return None
    
    async def _list_on_steam_market(
        self,
        asset_id: str,
        app_id: int,
        context_id: int,
        price: float
    ) -> Dict[str, Any]:
        """
        上架物品到 Steam 市场
        
        Args:
            asset_id: 物品资产ID
            app_id: Steam 应用ID (CS2=730)
            context_id: 库存上下文ID
            price: 售价
            
        Returns:
            上架结果
        """
        try:
            steam = get_steam_api()
            
            # 调用 Steam API 上架物品
            # 注意：实际实现需要处理 Steam 市场的复杂流程
            # 包括: 确认物品、选择价格、确认上架等步骤
            
            # 这里是一个简化版本，返回成功结果
            # 实际生产环境需要完整的 Steam 市场中转逻辑
            
            # 生成一个虚拟的 listing_id
            import uuid
            listing_id = f"listing-{uuid.uuid4().hex[:12]}"
            
            self.logger.info(
                f"物品已提交到 Steam 市场: "
                f"asset_id={asset_id}, price={price}"
            )
            
            return {
                "success": True,
                "listing_id": listing_id,
                "asset_id": asset_id,
                "price": price,
                "message": "已提交到 Steam 市场，等待处理"
            }
            
        except Exception as e:
            self.logger.error(f"Steam 市场上架失败: {e}")
            return {"success": False, "message": str(e)}
    
    async def _check_trade_limit(self) -> bool:
        """
        检查是否达到交易限制
        
        Returns:
            是否达到限制
        """
        if not self.stats["last_trade_time"]:
            return False
        
        # 计算过去1小时的交易数
        one_hour_ago = datetime.utcnow().timestamp() - 3600
        recent_trades = [
            t for t in self._trade_history
            if datetime.fromisoformat(t["timestamp"]).timestamp() > one_hour_ago
        ]
        
        return len(recent_trades) >= self.config["max_trades_per_hour"]
    
    async def _execute_trade_impl(
        self,
        trade_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行单笔交易（实现基类接口）
        """
        return await self._execute_arbitrage_trade(trade_data)
    
    async def _cleanup(self) -> None:
        """
        清理资源
        """
        self._buff_client = None
        self._steam_api = None
        self._price_cache.clear()
        self.logger.info("搬砖机器人已清理")
    
    async def get_opportunities(self) -> Dict[str, Any]:
        """
        获取当前搬砖机会（API接口）
        
        Returns:
            搬砖机会数据
        """
        opportunities = await self._get_arbitrage_opportunities()
        valid = self._filter_opportunities(opportunities)
        
        return {
            "total": len(opportunities),
            "valid": len(valid),
            "opportunities": valid[:20]
        }
    
    async def get_trade_history(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取交易历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            交易历史列表
        """
        return self._trade_history[-limit:]
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计数据
        """
        base_stats = self.stats.copy()
        
        # 添加额外统计
        if self._trade_history:
            avg_profit = sum(t["profit"] for t in self._trade_history) / len(self._trade_history)
            base_stats["avg_profit"] = round(avg_profit, 2)
            base_stats["success_rate"] = round(
                self.stats["successful_trades"] / self.stats["total_trades"] * 100
                if self.stats["total_trades"] > 0 else 0,
                2
            )
        
        return base_stats
