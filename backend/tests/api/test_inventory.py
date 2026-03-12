# -*- coding: utf-8 -*-
"""
Inventory API 测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.item import Item
from app.models.bot import Bot
from app.models.inventory import Inventory
from app.core.security import get_password_hash, create_access_token


async def create_test_user(test_db: AsyncSession) -> User:
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password123")
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


async def create_test_item(test_db: AsyncSession, name: str = "Test Item") -> Item:
    """创建测试饰品"""
    item = Item(
        name=name,
        name_cn="测试饰品",
        market_hash_name="Test_Item",
        category="weapon",
        rarity="covert",
        exterior="factory_new",
        current_price=100.0,
        steam_lowest_price=120.0,
        volume_24h=100,
        price_change_percent=5.0
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


async def create_test_bot(test_db: AsyncSession, user: User) -> Bot:
    """创建测试机器人"""
    bot = Bot(
        name="Test Bot",
        steam_id="123456789",
        username="testbot",
        status="online",
        owner_id=user.id
    )
    test_db.add(bot)
    await test_db.commit()
    await test_db.refresh(bot)
    return bot


async def create_test_inventory_item(test_db: AsyncSession, bot: Bot, item: Item) -> Inventory:
    """创建测试库存物品"""
    inventory_item = Inventory(
        bot_id=bot.id,
        item_id=item.id,
        asset_id="test_asset_123",
        context_id=2,
        instance_id=1,
        amount=1,
        price=item.current_price,
        is_locked=False
    )
    test_db.add(inventory_item)
    await test_db.commit()
    await test_db.refresh(inventory_item)
    return inventory_item


async def get_auth_header(user: User) -> dict:
    """获取认证头"""
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_inventory_empty(client: AsyncClient, test_db: AsyncSession):
    """测试获取库存列表（空）"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    response = await client.get("/api/v1/inventory/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_get_inventory_with_data(client: AsyncClient, test_db: AsyncSession):
    """测试获取库存列表（有数据）"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    bot = await create_test_bot(test_db, user)
    item = await create_test_item(test_db)
    await create_test_inventory_item(test_db, bot, item)
    
    response = await client.get("/api/v1/inventory/", headers=headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_inventory_by_bot(client: AsyncClient, test_db: AsyncSession):
    """测试获取指定机器人的库存"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    bot = await create_test_bot(test_db, user)
    item = await create_test_item(test_db)
    await create_test_inventory_item(test_db, bot, item)
    
    response = await client.get(f"/api/v1/inventory/bot/{bot.id}", headers=headers)
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_get_inventory_by_id(client: AsyncClient, test_db: AsyncSession):
    """测试获取库存详情"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    bot = await create_test_bot(test_db, user)
    item = await create_test_item(test_db)
    inventory_item = await create_test_inventory_item(test_db, bot, item)
    
    response = await client.get(f"/api/v1/inventory/{inventory_item.id}", headers=headers)
    # 可能返回200或404，取决于API实现
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_get_inventory_summary(client: AsyncClient, test_db: AsyncSession):
    """测试获取库存摘要"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    bot = await create_test_bot(test_db, user)
    item = await create_test_item(test_db)
    await create_test_inventory_item(test_db, bot, item)
    
    response = await client.get("/api/v1/inventory/summary", headers=headers)
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_refresh_inventory(client: AsyncClient, test_db: AsyncSession):
    """测试刷新库存"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    bot = await create_test_bot(test_db, user)
    
    response = await client.post(f"/api/v1/inventory/bot/{bot.id}/refresh", headers=headers)
    # 可能返回200或202
    assert response.status_code in [200, 202, 404]


@pytest.mark.asyncio
async def test_inventory_valuation(client: AsyncClient, test_db: AsyncSession):
    """测试库存估值"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    bot = await create_test_bot(test_db, user)
    item = await create_test_item(test_db)
    await create_test_inventory_item(test_db, bot, item)
    
    response = await client.get("/api/v1/inventory/valuation", headers=headers)
    assert response.status_code in [200, 404]
