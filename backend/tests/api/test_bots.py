# -*- coding: utf-8 -*-
"""
Bot API 测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.bot import Bot
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


async def get_auth_header(user: User) -> dict:
    """获取认证头"""
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_bots_empty(client: AsyncClient, test_db: AsyncSession):
    """测试获取机器人列表（空）"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    response = await client.get("/api/v1/bots/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    # API 返回列表格式
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_bot(client: AsyncClient, test_db: AsyncSession):
    """测试创建机器人"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    response = await client.post(
        "/api/v1/bots/",
        headers=headers,
        json={
            "name": "Test Bot",
            "steam_id": "123456789",
            "username": "testbot"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Bot"
    assert data["status"] == "offline"


@pytest.mark.asyncio
async def test_get_bot(client: AsyncClient, test_db: AsyncSession):
    """测试获取机器人详情"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    # 先创建机器人
    create_response = await client.post(
        "/api/v1/bots/",
        headers=headers,
        json={"name": "Test Bot"}
    )
    bot_id = create_response.json()["id"]
    
    # 获取详情
    response = await client.get(f"/api/v1/bots/{bot_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Bot"


@pytest.mark.asyncio
async def test_update_bot(client: AsyncClient, test_db: AsyncSession):
    """测试更新机器人"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    # 先创建机器人
    create_response = await client.post(
        "/api/v1/bots/",
        headers=headers,
        json={"name": "Test Bot"}
    )
    bot_id = create_response.json()["id"]
    
    # 更新
    response = await client.put(
        f"/api/v1/bots/{bot_id}",
        headers=headers,
        json={"name": "Updated Bot"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Bot"


@pytest.mark.asyncio
async def test_delete_bot(client: AsyncClient, test_db: AsyncSession):
    """测试删除机器人"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    # 先创建机器人
    create_response = await client.post(
        "/api/v1/bots/",
        headers=headers,
        json={"name": "Test Bot"}
    )
    bot_id = create_response.json()["id"]
    
    # 删除
    response = await client.delete(f"/api/v1/bots/{bot_id}", headers=headers)
    assert response.status_code == 204
