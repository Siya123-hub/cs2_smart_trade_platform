# -*- coding: utf-8 -*-
"""
机器人端点 v2
增强版 - 完整的CRUD操作和启动/停止控制
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.bot import Bot, BotTrade
from app.schemas.bot import (
    BotCreate,
    BotUpdate,
    BotResponse,
    BotLoginRequest,
    BotLoginResponse,
    BotInventoryResponse,
    BotInventoryItem,
    BotTradeResponse,
)

router = APIRouter()


@router.get("/", response_model=List[BotResponse])
async def get_bots(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取机器人列表 v2"""
    query = select(Bot).where(Bot.owner_id == current_user.id)
    
    if status_filter:
        query = query.where(Bot.status == status_filter)
    
    query = query.offset(skip).limit(limit).order_by(Bot.created_at.desc())
    result = await db.execute(query)
    bots = result.scalars().all()
    
    return bots


@router.post("/", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    bot_data: BotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建机器人 v2"""
    # 检查Steam ID是否已存在
    result = await db.execute(
        select(Bot).where(
            Bot.steam_id == bot_data.steam_id,
            Bot.owner_id == current_user.id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该Steam ID的机器人已存在"
        )
    
    bot = Bot(
        name=bot_data.name,
        steam_id=bot_data.steam_id,
        username=bot_data.username,
        session_token=bot_data.session_token,
        ma_file=bot_data.ma_file,
        access_token=bot_data.access_token,
        owner_id=current_user.id,
        status='offline'
    )
    db.add(bot)
    await db.commit()
    await db.refresh(bot)
    
    return bot


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取单个机器人详情 v2"""
    result = await db.execute(
        select(Bot).where(
            Bot.id == bot_id,
            Bot.owner_id == current_user.id
        )
    )
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="机器人不存在"
        )
    
    return bot


@router.put("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: int,
    bot_data: BotUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新机器人 v2"""
    result = await db.execute(
        select(Bot).where(
            Bot.id == bot_id,
            Bot.owner_id == current_user.id
        )
    )
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="机器人不存在"
        )
    
    # 更新字段
    update_data = bot_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(bot, key, value)
    
    bot.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(bot)
    
    return bot


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除机器人 v2"""
    result = await db.execute(
        select(Bot).where(
            Bot.id == bot_id,
            Bot.owner_id == current_user.id
        )
    )
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="机器人不存在"
        )
    
    # 检查机器人是否在线
    if bot.status == 'online':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先停止机器人再删除"
        )
    
    await db.delete(bot)
    await db.commit()
    
    return None


@router.post("/{bot_id}/start", response_model=BotResponse)
async def start_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """启动机器人 v2"""
    result = await db.execute(
        select(Bot).where(
            Bot.id == bot_id,
            Bot.owner_id == current_user.id
        )
    )
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="机器人不存在"
        )
    
    if bot.status == 'online':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="机器人已在运行中"
        )
    
    # 验证认证信息
    if not bot.session_token and not bot.ma_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="机器人缺少认证信息"
        )
    
    # TODO: 实现实际的机器人启动逻辑
    # 这里只是更新状态
    bot.status = 'online'
    bot.last_online = datetime.utcnow()
    bot.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(bot)
    
    return bot


@router.post("/{bot_id}/stop", response_model=BotResponse)
async def stop_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """停止机器人 v2"""
    result = await db.execute(
        select(Bot).where(
            Bot.id == bot_id,
            Bot.owner_id == current_user.id
        )
    )
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="机器人不存在"
        )
    
    if bot.status == 'offline':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="机器人已停止"
        )
    
    # TODO: 实现实际的机器人停止逻辑
    bot.status = 'offline'
    bot.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(bot)
    
    return bot


@router.post("/{bot_id}/restart", response_model=BotResponse)
async def restart_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """重启机器人 v2"""
    # 先停止
    result = await db.execute(
        select(Bot).where(
            Bot.id == bot_id,
            Bot.owner_id == current_user.id
        )
    )
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="机器人不存在"
        )
    
    # 重启逻辑
    bot.status = 'online'
    bot.last_online = datetime.utcnow()
    bot.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(bot)
    
    return bot


@router.get("/{bot_id}/inventory", response_model=BotInventoryResponse)
async def get_bot_inventory(
    bot_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取机器人库存 v2"""
    result = await db.execute(
        select(Bot).where(
            Bot.id == bot_id,
            Bot.owner_id == current_user.id
        )
    )
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="机器人不存在"
        )
    
    # TODO: 实现实际的库存获取逻辑
    # 返回模拟数据
    return BotInventoryResponse(
        bot_id=bot_id,
        items=[],
        total=0
    )


@router.get("/{bot_id}/trades", response_model=List[BotTradeResponse])
async def get_bot_trades(
    bot_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取机器人交易记录 v2"""
    result = await db.execute(
        select(Bot).where(
            Bot.id == bot_id,
            Bot.owner_id == current_user.id
        )
    )
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="机器人不存在"
        )
    
    query = select(BotTrade).where(BotTrade.bot_id == bot_id)
    
    if status_filter:
        query = query.where(BotTrade.status == status_filter)
    
    query = query.offset(skip).limit(limit).order_by(BotTrade.created_at.desc())
    result = await db.execute(query)
    trades = result.scalars().all()
    
    return trades


@router.get("/stats/summary")
async def get_bots_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取机器人统计摘要 v2"""
    # 统计各状态的机器人数量
    result = await db.execute(
        select(Bot.status, func.count(Bot.id))
        .where(Bot.owner_id == current_user.id)
        .group_by(Bot.status)
    )
    
    status_counts = {row[0]: row[1] for row in result.all()}
    
    # 总数
    total_result = await db.execute(
        select(func.count(Bot.id)).where(Bot.owner_id == current_user.id)
    )
    total = total_result.scalar() or 0
    
    return {
        "total": total,
        "online": status_counts.get('online', 0),
        "offline": status_counts.get('offline', 0),
        "error": status_counts.get('error', 0),
        "maintenance": status_counts.get('maintenance', 0)
    }
