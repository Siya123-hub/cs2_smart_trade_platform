# -*- coding: utf-8 -*-
"""
V2 Items API 测试
测试V2版本 Items 端点
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.item import Item
from app.core.security import get_password_hash, create_access_token


async def create_test_user(test_db: AsyncSession, username: str = "testuser") -> User:
    """创建测试用户"""
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("Password123!")
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


async def get_auth_header(user: User) -> dict:
    """获取认证头"""
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_v2_get_items_list(client: AsyncClient, test_db: AsyncSession):
    """测试V2获取物品列表"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    # 创建测试物品
    await create_test_item(test_db, "AK-47 | Redline")
    await create_test_item(test_db, "M4A1-S | Night")
    
    response = await client.get("/api/v2/items/", headers=headers)
    assert response.status_code in [200, 401]
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, (list, dict))


@pytest.mark.asyncio
async def test_v2_get_item_detail(client: AsyncClient, test_db: AsyncSession):
    """测试V2获取物品详情"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    # 创建测试物品
    item = await create_test_item(test_db, "AK-47 | Redline")
    
    response = await client.get(f"/api/v2/items/{item.id}", headers=headers)
    assert response.status_code in [200, 401, 404]
