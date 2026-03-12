# -*- coding: utf-8 -*-
"""
订单端点
"""
import asyncio
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.exceptions import NotFoundError, BusinessError
from app.core.idempotency import (
    generate_idempotency_key,
    check_idempotency,
    save_idempotent_response,
)
from app.models.user import User
from app.models.order import Order
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderListResponse,
    OrderCancelRequest,
    OrderStatus,
)
from app.utils.validators import validate_item_id, validate_price, validate_quantity, validate_order_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=OrderListResponse)
async def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    side: Optional[str] = None,
    source: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取订单列表"""
    # 构建基础过滤条件
    filters = [Order.user_id == current_user.id]
    
    if status:
        filters.append(Order.status == status)
    if side:
        filters.append(Order.side == side)
    if source:
        filters.append(Order.source == source)
    
    # 使用 func.count() 获取总数（不加载所有数据到内存）
    count_query = select(func.count()).select_from(Order).where(and_(*filters))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # 使用 selectinload 预加载关联数据，避免 N+1 查询
    query = (
        select(Order)
        .where(and_(*filters))
        .options(selectinload(Order.user), selectinload(Order.item))
        .order_by(Order.created_at.desc())
    )
    
    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return {
        "orders": orders,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_async_confirm: bool = Header(False, alias="X-Async-Confirm", description="是否异步确认订单"),
):
    """创建订单（支持幂等性和异步确认）
    
    Args:
        idempotency_key: 幂等性 key，避免重复创建订单
        x_async_confirm: 是否异步确认订单（后台处理）
    """
    # 如果提供了幂等性 key，进行检查
    if idempotency_key:
        # 生成内部幂等性 key
        internal_key = generate_idempotency_key(
            current_user.id,
            "POST",
            "/api/v1/orders",
            f"{order_data.item_id}:{order_data.side}:{order_data.price}:{order_data.quantity}"
        )
        
        # 检查是否已处理过
        is_duplicate, cached_response = await check_idempotency(internal_key)
        if is_duplicate and cached_response:
            logger.info(f"检测到重复订单请求，key: {idempotency_key}")
            return cached_response
    
    # 使用验证器验证输入数据
    validated_item_id = validate_item_id(order_data.item_id)
    validated_price = validate_price(order_data.price)
    validated_quantity = validate_quantity(order_data.quantity)
    
    # ========== 交易限额检查 ==========
    # 计算订单总金额
    order_total = validated_price * validated_quantity
    
    # 检查用户余额是否充足（仅针对购买订单）
    if order_data.side.value == "buy":
        # 获取用户当前余额
        user_balance = current_user.balance or 0
        if isinstance(user_balance, str):
            user_balance = float(user_balance)
        
        if user_balance < order_total:
            raise BusinessError(
                f"余额不足: 当前余额 {user_balance:.2f}，订单金额 {order_total:.2f}"
            )
        
        # 检查单笔订单限额
        MAX_SINGLE_ORDER = 10000.0  # 单笔订单最大金额
        if order_total > MAX_SINGLE_ORDER:
            raise BusinessError(
                f"单笔订单金额超限: 最大 {MAX_SINGLE_ORDER:.2f}，订单金额 {order_total:.2f}"
            )
        
        # 检查日累计限额
        from datetime import datetime, timedelta
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 查询今日已成交的订单总金额
        daily_orders_query = select(func.sum(Order.price * Order.quantity)).where(
            and_(
                Order.user_id == current_user.id,
                Order.side == "buy",
                Order.status.in_(["completed", "filled"]),  # 只计算已完成的订单
                Order.created_at >= today_start
            )
        )
        daily_result = await db.execute(daily_orders_query)
        daily_total = daily_result.scalar() or 0
        if isinstance(daily_total, str):
            daily_total = float(daily_total)
        
        MAX_DAILY_LIMIT = 50000.0  # 每日累计最大交易金额
        if daily_total + order_total > MAX_DAILY_LIMIT:
            raise BusinessError(
                f"今日交易限额已用完: 今日已交易 {daily_total:.2f}，限额 {MAX_DAILY_LIMIT:.2f}"
            )
    
    # 生成订单号
    import uuid
    order_id = f"ORD-{uuid.uuid4().hex[:12].upper()}"
    
    # 根据是否异步确认设置初始状态
    initial_status = "pending_confirm" if x_async_confirm else "pending"
    
    order = Order(
        order_id=order_id,
        user_id=current_user.id,
        item_id=validated_item_id,
        side=order_data.side,
        price=validated_price,
        quantity=validated_quantity,
        source=order_data.source.value,
        status=initial_status,
    )
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    # 如果启用异步确认，后台处理订单
    if x_async_confirm:
        asyncio.create_task(_async_confirm_order(order_id, db))
        logger.info(f"订单 {order_id} 已创建，等待异步确认")
    
    # 构建响应数据
    response_data = OrderResponse.model_validate(order).model_dump()
    
    # 如果提供了幂等性 key，保存响应
    if idempotency_key:
        await save_idempotent_response(internal_key, response_data)
    
    return response_data


async def _async_confirm_order(order_id: str, db: AsyncSession):
    """
    异步确认订单（后台任务）
    
    负责检查订单是否可执行并更新状态
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    
    try:
        # 查询订单
        result = await db.execute(
            select(Order).where(Order.order_id == order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            logger.error(f"异步确认失败：订单 {order_id} 不存在")
            return
        
        # 模拟订单处理逻辑
        # 实际应该调用交易引擎执行订单
        
        # 更新订单状态为 pending（可执行）
        order.status = "pending"
        await db.commit()
        
        logger.info(f"订单 {order_id} 异步确认完成，状态更新为 pending")
        
    except Exception as e:
        logger.error(f"订单 {order_id} 异步确认失败: {e}")
        try:
            # 更新订单状态为失败
            result = await db.execute(
                select(Order).where(Order.order_id == order_id)
            )
            order = result.scalar_one_or_none()
            if order:
                order.status = "failed"
                await db.commit()
        except Exception:
            pass


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取订单详情"""
    # 使用验证器验证order_id
    validated_order_id = validate_order_id(order_id)
    
    result = await db.execute(
        select(Order).where(
            and_(Order.order_id == validated_order_id, Order.user_id == current_user.id)
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise NotFoundError("订单", validated_order_id)
    
    return order


@router.delete("/{order_id}")
async def cancel_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消订单"""
    # 使用验证器验证order_id
    validated_order_id = validate_order_id(order_id)
    
    result = await db.execute(
        select(Order).where(
            and_(Order.order_id == validated_order_id, Order.user_id == current_user.id)
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise NotFoundError("订单", validated_order_id)
    
    if order.status != "pending":
        raise BusinessError("只能取消待处理的订单")
    
    from datetime import datetime
    order.status = "cancelled"
    order.cancelled_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "订单已取消", "order_id": order_id}
