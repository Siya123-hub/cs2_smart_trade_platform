# -*- coding: utf-8 -*-
"""
监控端点 v2
增强版 - 完整的CRUD操作和启用/停用控制
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.monitor import MonitorTask, MonitorLog
from app.schemas.monitor import (
    MonitorCreate,
    MonitorUpdate,
    MonitorResponse,
    MonitorListResponse,
    MonitorLogResponse,
    MonitorLogListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=MonitorListResponse)
async def get_monitors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    enabled: Optional[bool] = None,
    task_status: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取监控任务列表 v2"""
    query = select(MonitorTask).where(MonitorTask.user_id == current_user.id)
    
    if enabled is not None:
        query = query.where(MonitorTask.enabled == enabled)
    
    if task_status:
        query = query.where(MonitorTask.status == task_status)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页
    query = query.offset(skip).limit(limit).order_by(MonitorTask.created_at.desc())
    result = await db.execute(query)
    monitors = result.scalars().all()
    
    return MonitorListResponse(
        monitors=monitors,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_monitor(
    monitor_data: MonitorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建监控任务 v2"""
    # 检查同名监控是否已存在
    result = await db.execute(
        select(MonitorTask).where(
            MonitorTask.name == monitor_data.name,
            MonitorTask.user_id == current_user.id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="同名监控任务已存在"
        )
    
    monitor = MonitorTask(
        name=monitor_data.name,
        monitor_type=monitor_data.monitor_type,
        target_url=monitor_data.target_url,
        condition_type=monitor_data.condition_type,
        condition_value=monitor_data.condition_value,
        enabled=True,
        user_id=current_user.id,
        status='idle'
    )
    
    db.add(monitor)
    await db.commit()
    await db.refresh(monitor)
    
    logger.info(f"用户 {current_user.id} 创建了监控任务: {monitor.name}")
    
    return monitor


@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取单个监控任务 v2"""
    result = await db.execute(
        select(MonitorTask).where(
            MonitorTask.id == monitor_id,
            MonitorTask.user_id == current_user.id
        )
    )
    monitor = result.scalar_one_or_none()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="监控任务不存在"
        )
    
    return monitor


@router.put("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
    monitor_id: int,
    monitor_data: MonitorUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新监控任务 v2"""
    result = await db.execute(
        select(MonitorTask).where(
            MonitorTask.id == monitor_id,
            MonitorTask.user_id == current_user.id
        )
    )
    monitor = result.scalar_one_or_none()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="监控任务不存在"
        )
    
    # 更新字段
    update_data = monitor_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(monitor, key, value)
    
    monitor.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(monitor)
    
    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除监控任务 v2"""
    result = await db.execute(
        select(MonitorTask).where(
            MonitorTask.id == monitor_id,
            MonitorTask.user_id == current_user.id
        )
    )
    monitor = result.scalar_one_or_none()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="监控任务不存在"
        )
    
    # 删除关联的日志
    await db.execute(
        delete(MonitorLog).where(MonitorLog.monitor_id == monitor_id)
    )
    
    await db.delete(monitor)
    await db.commit()
    
    return None


@router.post("/{monitor_id}/enable", response_model=MonitorResponse)
async def enable_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """启用监控任务 v2"""
    result = await db.execute(
        select(MonitorTask).where(
            MonitorTask.id == monitor_id,
            MonitorTask.user_id == current_user.id
        )
    )
    monitor = result.scalar_one_or_none()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="监控任务不存在"
        )
    
    if monitor.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="监控任务已启用"
        )
    
    monitor.enabled = True
    monitor.status = 'running'
    monitor.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(monitor)
    
    logger.info(f"用户 {current_user.id} 启用了监控任务: {monitor.name}")
    
    return monitor


@router.post("/{monitor_id}/disable", response_model=MonitorResponse)
async def disable_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """停用监控任务 v2"""
    result = await db.execute(
        select(MonitorTask).where(
            MonitorTask.id == monitor_id,
            MonitorTask.user_id == current_user.id
        )
    )
    monitor = result.scalar_one_or_none()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="监控任务不存在"
        )
    
    if not monitor.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="监控任务已停用"
        )
    
    monitor.enabled = False
    monitor.status = 'stopped'
    monitor.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(monitor)
    
    logger.info(f"用户 {current_user.id} 停用了监控任务: {monitor.name}")
    
    return monitor


@router.post("/{monitor_id}/trigger", response_model=MonitorResponse)
async def trigger_monitor(
    monitor_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """手动触发监控任务 v2"""
    result = await db.execute(
        select(MonitorTask).where(
            MonitorTask.id == monitor_id,
            MonitorTask.user_id == current_user.id
        )
    )
    monitor = result.scalar_one_or_none()
    
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="监控任务不存在"
        )
    
    if not monitor.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先启用监控任务"
        )
    
    # 实现实际的监控触发逻辑
    # 根据监控类型执行相应的检查
    try:
        if monitor.monitor_type == 'price':
            # 价格监控：检查目标价格是否达到
            from app.services.pricing import PricingService
            pricing_service = PricingService()
            # 获取最新价格并比较
            current_price = await pricing_service.get_item_price(monitor.target_url)
            if current_price and current_price <= float(monitor.threshold_price or 0):
                monitor.trigger_count += 1
                monitor.last_triggered = datetime.utcnow()
        elif monitor.monitor_type == 'inventory':
            # 库存监控：检查库存变化
            from app.services.steam import SteamService
            steam_service = SteamService()
            inventory = await steam_service.get_inventory(monitor.bot_id)
            if inventory:
                monitor.trigger_count += 1
                monitor.last_triggered = datetime.utcnow()
        elif monitor.monitor_type == 'profit':
            # 利润监控：检查利润机会
            from app.services.buff import BuffService
            buff_service = BuffService()
            opportunities = await buff_service.check_profit_opportunities()
            if opportunities:
                monitor.trigger_count += 1
                monitor.last_triggered = datetime.utcnow()
    except Exception as e:
        # 记录错误但不影响主流程
        import logging
        logging.error(f"监控触发失败: {str(e)}")
    
    monitor.last_triggered = datetime.utcnow()
    monitor.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(monitor)
    
    return monitor


@router.get("/{monitor_id}/logs", response_model=MonitorLogListResponse)
async def get_monitor_logs(
    monitor_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取监控日志 v2"""
    # 验证监控任务归属
    result = await db.execute(
        select(MonitorTask).where(
            MonitorTask.id == monitor_id,
            MonitorTask.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="监控任务不存在"
        )
    
    # 获取日志
    query = select(MonitorLog).where(MonitorLog.monitor_id == monitor_id)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页
    query = query.offset(skip).limit(limit).order_by(MonitorLog.created_at.desc())
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return MonitorLogListResponse(
        logs=logs,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/stats/summary")
async def get_monitors_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取监控统计摘要 v2"""
    # 统计各状态的监控数量
    status_result = await db.execute(
        select(MonitorTask.status, func.count(MonitorTask.id))
        .where(MonitorTask.user_id == current_user.id)
        .group_by(MonitorTask.status)
    )
    status_counts = {row[0]: row[1] for row in status_result.all()}
    
    # 启用的监控
    enabled_result = await db.execute(
        select(func.count(MonitorTask.id))
        .where(MonitorTask.user_id == current_user.id, MonitorTask.enabled == True)
    )
    enabled_count = enabled_result.scalar() or 0
    
    # 总数
    total_result = await db.execute(
        select(func.count(MonitorTask.id)).where(MonitorTask.user_id == current_user.id)
    )
    total = total_result.scalar() or 0
    
    return {
        "total": total,
        "enabled": enabled_count,
        "disabled": total - enabled_count,
        "running": status_counts.get('running', 0),
        "stopped": status_counts.get('stopped', 0),
        "idle": status_counts.get('idle', 0),
        "error": status_counts.get('error', 0)
    }
