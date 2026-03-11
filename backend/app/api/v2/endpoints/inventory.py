# -*- coding: utf-8 -*-
"""
库存端点 v2
增强版 - 完整的库存管理和同步功能
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.inventory import Inventory, Listing
from app.schemas.inventory import (
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse,
    InventoryListResponse,
    SyncInventoryResponse,
    ListingCreate,
    ListingResponse,
    ListingListResponse,
    BatchListingRequest,
    BatchUnlistRequest,
    BatchResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=InventoryListResponse)
async def get_inventory(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    rarity: Optional[str] = None,
    sort_by: str = Query("acquired_at", regex="^(acquired_at|price|name)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户库存列表 v2"""
    query = select(Inventory).where(Inventory.user_id == current_user.id)
    
    if status_filter:
        query = query.where(Inventory.status == status_filter)
    
    if search:
        query = query.where(Inventory.name.ilike(f"%{search}%"))
    
    if rarity:
        query = query.where(Inventory.rarity == rarity)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 排序
    sort_column = getattr(Inventory, sort_by, Inventory.acquired_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # 分页
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return InventoryListResponse(
        items=[InventoryResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{item_id}", response_model=InventoryResponse)
async def get_inventory_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取单个库存物品详情 v2"""
    result = await db.execute(
        select(Inventory).where(
            Inventory.id == item_id,
            Inventory.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="库存物品不存在"
        )
    
    return InventoryResponse.model_validate(item)


@router.put("/{item_id}", response_model=InventoryResponse)
async def update_inventory_item(
    item_id: int,
    item_data: InventoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新库存物品 v2"""
    result = await db.execute(
        select(Inventory).where(
            Inventory.id == item_id,
            Inventory.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="库存物品不存在"
        )
    
    # 更新字段
    update_data = item_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    
    return InventoryResponse.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除库存物品 v2"""
    result = await db.execute(
        select(Inventory).where(
            Inventory.id == item_id,
            Inventory.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="库存物品不存在"
        )
    
    if item.status == 'listed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先下架物品再删除"
        )
    
    await db.delete(item)
    await db.commit()
    
    return None


@router.post("/sync", response_model=SyncInventoryResponse)
async def sync_inventory(
    platform: str = Query(..., description="同步平台: steam/buff"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """同步库存 v2"""
    # 实现实际的平台库存同步逻辑
    synced_count = 0
    
    if platform == 'steam':
        # Steam库存同步
        try:
            from app.services.steam import SteamService
            steam_service = SteamService()
            # 获取用户的机器人
            from app.models.bot import Bot
            bots_result = await db.execute(
                select(Bot).where(Bot.owner_id == current_user.id)
            )
            bots = bots_result.scalars().all()
            
            for bot in bots:
                inventory_data = await steam_service.get_inventory(bot.id)
                if inventory_data:
                    for item in inventory_data:
                        existing = await db.execute(
                            select(Inventory).where(
                                Inventory.asset_id == item.get('asset_id'),
                                Inventory.user_id == current_user.id
                            )
                        )
                        if existing.scalar_one_or_none():
                            continue
                        new_inv = Inventory(
                            user_id=current_user.id,
                            bot_id=bot.id,
                            asset_id=item.get('asset_id'),
                            market_hash_name=item.get('market_hash_name', ''),
                            price=item.get('price', 0.0),
                            quantity=item.get('quantity', 1)
                        )
                        db.add(new_inv)
                        synced_count += 1
        except Exception as e:
            import logging
            logging.error(f"Steam同步失败: {str(e)}")
    
    elif platform == 'buff':
        # BUFF库存同步
        try:
            from app.services.buff import BuffService
            buff_service = BuffService()
            buff_inventory = await buff_service.get_inventory(current_user.id)
            
            for item in buff_inventory:
                existing = await db.execute(
                    select(Inventory).where(
                        Inventory.market_hash_name == item.get('market_hash_name'),
                        Inventory.user_id == current_user.id
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                new_inv = Inventory(
                    user_id=current_user.id,
                    market_hash_name=item.get('market_hash_name', ''),
                    price=item.get('price', 0.0),
                    quantity=item.get('quantity', 1)
                )
                db.add(new_inv)
                synced_count += 1
        except Exception as e:
            import logging
            logging.error(f"BUFF同步失败: {str(e)}")
    
    # 获取同步后的总库存
    result = await db.execute(
        select(func.count(Inventory.id))
        .where(Inventory.user_id == current_user.id)
    )
    current_count = result.scalar() or 0
    
    return SyncInventoryResponse(
        platform=platform,
        synced_items=synced_count,
        total_items=current_count,
        timestamp=datetime.utcnow()
    )


@router.post("/batch-list", response_model=BatchResponse)
async def batch_list_items(
    request: BatchListingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量上架物品 v2"""
    success_count = 0
    failed_items = []
    
    for item_id in request.item_ids:
        try:
            result = await db.execute(
                select(Inventory).where(
                    Inventory.id == item_id,
                    Inventory.user_id == current_user.id
                )
            )
            item = result.scalar_one_or_none()
            
            if not item:
                failed_items.append({"id": item_id, "error": "物品不存在"})
                continue
            
            if item.status == 'listed':
                failed_items.append({"id": item_id, "error": "物品已上架"})
                continue
            
            # 上架
            item.status = 'listed'
            item.listed_at = datetime.utcnow()
            item.updated_at = datetime.utcnow()
            success_count += 1
            
        except Exception as e:
            failed_items.append({"id": item_id, "error": str(e)})
    
    await db.commit()
    
    return BatchResponse(
        success=len(failed_items) == 0,
        total=len(request.item_ids),
        processed=success_count,
        failed=len(failed_items),
        details=failed_items
    )


@router.post("/batch-unlist", response_model=BatchResponse)
async def batch_unlist_items(
    request: BatchUnlistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量下架物品 v2"""
    success_count = 0
    failed_items = []
    
    for item_id in request.item_ids:
        try:
            result = await db.execute(
                select(Inventory).where(
                    Inventory.id == item_id,
                    Inventory.user_id == current_user.id
                )
            )
            item = result.scalar_one_or_none()
            
            if not item:
                failed_items.append({"id": item_id, "error": "物品不存在"})
                continue
            
            if item.status != 'listed':
                failed_items.append({"id": item_id, "error": "物品未上架"})
                continue
            
            # 下架
            item.status = 'owned'
            item.listed_at = None
            item.updated_at = datetime.utcnow()
            success_count += 1
            
        except Exception as e:
            failed_items.append({"id": item_id, "error": str(e)})
    
    await db.commit()
    
    return BatchResponse(
        success=len(failed_items) == 0,
        total=len(request.item_ids),
        processed=success_count,
        failed=len(failed_items),
        details=failed_items
    )


# ========== 挂售列表 ==========

@router.get("/listings", response_model=ListingListResponse)
async def get_listings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户的挂售列表 v2"""
    query = select(Listing).where(Listing.user_id == current_user.id)
    
    if status_filter:
        query = query.where(Listing.status == status_filter)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页
    query = query.offset(skip).limit(limit).order_by(Listing.created_at.desc())
    result = await db.execute(query)
    listings = result.scalars().all()
    
    return ListingListResponse(
        listings=[ListingResponse.model_validate(l) for l in listings],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/stats/summary")
async def get_inventory_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取库存统计摘要 v2"""
    # 总数
    total_result = await db.execute(
        select(func.count(Inventory.id)).where(Inventory.user_id == current_user.id)
    )
    total = total_result.scalar() or 0
    
    # 按状态统计
    status_result = await db.execute(
        select(Inventory.status, func.count(Inventory.id))
        .where(Inventory.user_id == current_user.id)
        .group_by(Inventory.status)
    )
    status_counts = {row[0]: row[1] for row in status_result.all()}
    
    # 挂售中
    listed_result = await db.execute(
        select(func.count(Listing.id)).where(Listing.user_id == current_user.id)
    )
    listed = listed_result.scalar() or 0
    
    return {
        "total": total,
        "owned": status_counts.get('owned', 0),
        "listed": status_counts.get('listed', 0),
        "pending": status_counts.get('pending', 0),
        "sold": status_counts.get('sold', 0),
        "active_listings": listed
    }
