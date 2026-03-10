# -*- coding: utf-8 -*-
"""
价格监控服务
"""
import asyncio
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta

import aiohttp

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.item import Item, PriceHistory
from app.models.monitor import MonitorTask, MonitorLog
from app.services.buff_service import get_buff_client
from app.services.steam_service import get_steam_api
from app.core.config import settings

logger = logging.getLogger(__name__)


class PriceMonitor:
    """价格监控服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.buff_client = get_buff_client()
        self.steam_api = get_steam_api()
        self.running = False
        self.monitor_tasks: Dict[int, MonitorTask] = {}
        self.alert_callbacks: List[Callable] = []
    
    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
    
    async def start(self):
        """启动监控"""
        self.running = True
        logger.info("价格监控服务已启动")
        
        # 启动各个监控任务
        asyncio.create_task(self.poll_buff_prices())
        asyncio.create_task(self.check_arbitrage())
    
    async def stop(self):
        """停止监控"""
        self.running = False
        logger.info("价格监控服务已停止")
    
    async def poll_buff_prices(self):
        """轮询 BUFF 价格"""
        while self.running:
            try:
                # 获取需要监控的饰品
                result = await self.db.execute(
                    select(Item).limit(100)
                )
                items = result.scalars().all()
                
                for item in items:
                    try:
                        # 获取 BUFF 价格
                        price_data = await self.buff_client.get_price_overview(
                            item.market_hash_name
                        )
                        
                        if price_data:
                            # 更新数据库
                            item.current_price = float(price_data.get("lowest_price", 0))
                            item.volume_24h = int(price_data.get("volume", 0))
                            
                            # 记录价格历史
                            history = PriceHistory(
                                item_id=item.id,
                                source="buff",
                                price=item.current_price,
                            )
                            self.db.add(history)
                            
                            # 检查监控规则
                            await self.check_monitors(item)
                    
                    except Exception as e:
                        logger.error(f"获取 {item.name} 价格失败: {e}")
                
                await self.db.commit()
                
            except Exception as e:
                logger.error(f"价格轮询错误: {e}")
            
            # 等待下一次轮询
            await asyncio.sleep(settings.PRICE_UPDATE_INTERVAL_HIGH)
    
    async def check_arbitrage(self):
        """检查搬砖机会"""
        while self.running:
            try:
                # 获取所有饰品
                result = await self.db.execute(
                    select(Item).where(
                        Item.current_price > 0,
                        Item.steam_lowest_price > 0
                    )
                )
                items = result.scalars().all()
                
                arbitrage_found = []
                
                for item in items:
                    # 计算搬砖利润
                    steam_sell = item.steam_lowest_price * 0.85
                    profit = steam_sell - item.current_price
                    
                    if profit >= settings.MIN_PROFIT:
                        arbitrage_found.append({
                            "item_id": item.id,
                            "name": item.name,
                            "buff_price": item.current_price,
                            "steam_price": item.steam_lowest_price,
                            "profit": profit,
                        })
                
                if arbitrage_found:
                    # 触发告警
                    for callback in self.alert_callbacks:
                        try:
                            callback(arbitrage_found)
                        except Exception as e:
                            logger.error(f"告警回调错误: {e}")
                
            except Exception as e:
                logger.error(f"套利检查错误: {e}")
            
            # 每分钟检查一次
            await asyncio.sleep(60)
    
    async def check_monitors(self, item: Item):
        """检查监控规则"""
        # 查询所有启用的监控任务
        result = await self.db.execute(
            select(MonitorTask).where(
                MonitorTask.enabled == True,
                MonitorTask.item_id == item.id
            )
        )
        tasks = result.scalars().all()
        
        for task in tasks:
            triggered = False
            message = ""
            
            if task.condition_type == "price_below":
                if item.current_price <= float(task.threshold):
                    triggered = True
                    message = f"{item.name} 价格低于 {task.threshold}，当前价格: {item.current_price}"
            
            elif task.condition_type == "price_above":
                if item.current_price >= float(task.threshold):
                    triggered = True
                    message = f"{item.name} 价格高于 {task.threshold}，当前价格: {item.current_price}"
            
            elif task.condition_type == "arbitrage":
                if item.current_price > 0 and item.steam_lowest_price > 0:
                    profit = item.steam_lowest_price * 0.85 - item.current_price
                    if profit >= float(task.threshold):
                        triggered = True
                        message = f"{item.name} 发现搬砖机会，利润: {profit}"
            
            if triggered:
                # 更新任务统计
                task.trigger_count += 1
                task.last_triggered = datetime.utcnow()
                
                # 记录日志
                log = MonitorLog(
                    task_id=task.id,
                    trigger_type="triggered",
                    message=message,
                    price_data=f'{{"price": {item.current_price}}}',
                )
                self.db.add(log)
                
                # 执行动作
                if task.action == "auto_buy":
                    # 执行自动买入
                    try:
                        from app.services.trading_service import TradingEngine
                        
                        trading_engine = TradingEngine(self.db)
                        
                        # 从任务配置中获取最大买入价格
                        max_price = float(task.threshold)
                        
                        # 执行买入（传递 user_id）
                        buy_result = await trading_engine.execute_buy(
                            item_id=item.id,
                            max_price=max_price,
                            user_id=task.user_id
                        )
                        
                        if buy_result.get("success"):
                            log.message += f" | 自动买入成功: {buy_result.get('order_id')}"
                        else:
                            log.message += f" | 自动买入失败: {buy_result.get('message')}"
                    except Exception as e:
                        log.message += f" | 自动买入异常: {str(e)}"
                
                await self.db.commit()
    
    async def create_monitor_task(
        self,
        name: str,
        item_id: int,
        condition_type: str,
        threshold: float,
        action: Optional[str] = None,
        user_id: int = None
    ) -> MonitorTask:
        """创建监控任务"""
        if user_id is None:
            raise ValueError("create_monitor_task 必须提供 user_id 参数")
        
        task = MonitorTask(
            name=name,
            item_id=item_id,
            condition_type=condition_type,
            threshold=threshold,
            action=action,
            user_id=user_id,
            enabled=True,
            status="idle",
        )
        
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        
        return task


# 全局监控实例
_monitor: Optional[PriceMonitor] = None


def get_price_monitor(db: AsyncSession) -> PriceMonitor:
    """获取价格监控实例"""
    global _monitor
    if _monitor is None:
        _monitor = PriceMonitor(db)
    return _monitor
