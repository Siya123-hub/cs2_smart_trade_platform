# -*- coding: utf-8 -*-
"""
订单确认服务
提供订单状态确认机制，确保订单状态同步
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.order import Order, OrderLog
from app.services.buff_service import get_buff_client
from app.services.cache import get_cache
from app.core.config import settings

logger = logging.getLogger(__name__)

# 订单确认配置 - 从 settings 读取
ORDER_CONFIRM_CHECK_INTERVAL = settings.ORDER_CONFIRM_CHECK_INTERVAL  # 检查间隔（秒）
ORDER_CONFIRM_TIMEOUT = settings.ORDER_CONFIRM_TIMEOUT  # 确认超时（秒）
ORDER_POLL_RETRIES = settings.ORDER_POLL_RETRIES  # 最大轮询次数


class OrderConfirmationStatus:
    """订单确认状态"""
    PENDING = "pending"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class OrderConfirmationService:
    """
    订单确认服务
    
    功能：
    - 异步确认订单状态
    - 防止订单状态更新丢失
    - 支持订单状态轮询
    - 提供订单确认超时处理
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._pending_confirmations: Dict[str, asyncio.Task] = {}
        self._confirmation_results: Dict[str, Dict[str, Any]] = {}
    
    async def confirm_order(
        self,
        order_id: str,
        external_order_id: str,
        source: str = "buff",
        timeout: int = ORDER_CONFIRM_TIMEOUT,
        check_interval: int = ORDER_CONFIRM_CHECK_INTERVAL
    ) -> Dict[str, Any]:
        """
        确认订单状态
        """
        logger.info(f"Starting order confirmation for order {order_id} (external: {external_order_id})")
        
        start_time = datetime.utcnow()
        retries = 0
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            try:
                status = await self._check_local_order_status(order_id)
                
                if status:
                    await self._update_order_status(order_id, status)
                    
                    result = {
                        "order_id": order_id,
                        "external_order_id": external_order_id,
                        "status": status,
                        "confirmed": True,
                        "retries": retries
                    }
                    
                    self._confirmation_results[order_id] = result
                    logger.info(f"Order {order_id} confirmed with status: {status}")
                    return result
                
                retries += 1
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error confirming order {order_id}: {e}")
                retries += 1
                await asyncio.sleep(check_interval)
        
        logger.warning(f"Order confirmation timeout for order {order_id}")
        await self._update_order_status(order_id, OrderConfirmationStatus.TIMEOUT)
        
        return {
            "order_id": order_id,
            "external_order_id": external_order_id,
            "status": OrderConfirmationStatus.TIMEOUT,
            "confirmed": False,
            "retries": retries,
            "error": "Confirmation timeout"
        }
    
    async def _check_local_order_status(self, order_id: str) -> Optional[str]:
        """检查本地订单状态"""
        try:
            result = await self.db.execute(
                select(Order).where(Order.order_id == order_id)
            )
            order = result.scalar_one_or_none()
            
            if order:
                if order.status in ["completed", "cancelled", "failed"]:
                    return order.status
                return None
            
            return None
        except Exception as e:
            logger.error(f"Error checking local order status: {e}")
            return None
    
    async def _update_order_status(self, order_id: str, status: str) -> None:
        """更新订单状态"""
        try:
            await self.db.execute(
                update(Order)
                .where(Order.order_id == order_id)
                .values(
                    status=status,
                    completed_at=datetime.utcnow() if status == "completed" else None
                )
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            await self.db.rollback()
    
    async def start_background_confirmation(
        self,
        order_id: str,
        external_order_id: str,
        source: str = "buff"
    ) -> None:
        """启动后台订单确认任务"""
        if order_id in self._pending_confirmations:
            logger.warning(f"Confirmation task already exists for order {order_id}")
            return
        
        task = asyncio.create_task(
            self.confirm_order(order_id, external_order_id, source)
        )
        self._pending_confirmations[order_id] = task
        
        task.add_done_callback(
            lambda t: self._pending_confirmations.pop(order_id, None)
        )
    
    async def get_confirmation_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """获取订单确认状态"""
        if order_id in self._pending_confirmations:
            task = self._pending_confirmations[order_id]
            if not task.done():
                return {
                    "order_id": order_id,
                    "status": OrderConfirmationStatus.CONFIRMING,
                    "confirmed": False
                }
        
        if order_id in self._confirmation_results:
            return self._confirmation_results[order_id]
        
        try:
            result = await self.db.execute(
                select(Order).where(Order.order_id == order_id)
            )
            order = result.scalar_one_or_none()
            
            if order:
                return {
                    "order_id": order_id,
                    "status": order.status,
                    "confirmed": order.status == OrderConfirmationStatus.CONFIRMED
                }
        except Exception as e:
            logger.error(f"Error getting confirmation status: {e}")
        
        return None
    
    async def cancel_confirmation(self, order_id: str) -> bool:
        """取消订单确认"""
        if order_id in self._pending_confirmations:
            task = self._pending_confirmations[order_id]
            task.cancel()
            self._pending_confirmations.pop(order_id, None)
            logger.info(f"Confirmation cancelled for order {order_id}")
            return True
        return False
    
    async def confirm_multiple_orders(
        self,
        orders: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """批量确认订单"""
        tasks = [
            self.confirm_order(
                order["order_id"],
                order.get("external_order_id", ""),
                order.get("source", "buff")
            )
            for order in orders
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "order_id": orders[i]["order_id"],
                    "status": OrderConfirmationStatus.FAILED,
                    "confirmed": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results


_confirmation_service: Optional[OrderConfirmationService] = None


def get_confirmation_service(db: AsyncSession) -> OrderConfirmationService:
    """获取订单确认服务实例"""
    global _confirmation_service
    _confirmation_service = OrderConfirmationService(db)
    return _confirmation_service
