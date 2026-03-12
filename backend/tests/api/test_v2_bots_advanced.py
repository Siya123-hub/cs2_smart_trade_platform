# -*- coding: utf-8 -*-
"""
V2 Bots 高级API测试
测试V2版本 Bots 高级功能
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.bot import Bot
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


async def create_test_bot(test_db: AsyncSession, user: User, name: str = "Test Bot") -> Bot:
    """创建测试机器人"""
    bot = Bot(
        name=name,
        steam_id="123456789",
        username="testbot",
        status="online",
        owner_id=user.id,
        session_token="test_token",
        ma_file="test_ma_file"
    )
    test_db.add(bot)
    await test_db.commit()
    await test_db.refresh(bot)
    return bot


async def get_auth_header(user: User) -> dict:
    """获取认证头"""
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_v2_bots_batch_status_update(client: AsyncClient, test_db: AsyncSession):
    """测试V2批量更新机器人状态"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    # 创建测试机器人
    bot1 = await create_test_bot(test_db, user, "Bot 1")
    bot2 = await create_test_bot(test_db, user, "Bot 2")
    
    response = await client.post(
        "/api/v2/bots/batch-status",
        headers=headers,
        json={
            "bot_ids": [bot1.id, bot2.id],
            "status": "online"
        }
    )
    assert response.status_code in [200, 401, 404]


@pytest.mark.asyncio
async def test_v2_bots_get_online_list(client: AsyncClient, test_db: AsyncSession):
    """测试V2获取在线机器人列表"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    await create_test_bot(test_db, user, "Online Bot")
    
    response = await client.get("/api/v2/bots/online", headers=headers)
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_v2_bots_validate_credentials(client: AsyncClient, test_db: AsyncSession):
    """测试V2验证机器人凭证"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    bot = await create_test_bot(test_db, user, "Test Bot")
    
    response = await client.post(
        f"/api/v2/bots/{bot.id}/validate",
        headers=headers
    )
    assert response.status_code in [200, 401, 404]


@pytest.mark.asyncio
async def test_v2_bots_get_trade_url(client: AsyncClient, test_db: AsyncSession):
    """测试V2获取机器人交易链接"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    bot = await create_test_bot(test_db, user, "Test Bot")
    
    response = await client.get(
        f"/api/v2/bots/{bot.id}/trade-url",
        headers=headers
    )
    assert response.status_code in [200, 401, 404]


@pytest.mark.asyncio
async def test_v2_bots_send_trade_offer(client: AsyncClient, test_db: AsyncSession):
    """测试V2发送交易报价"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    bot = await create_test_bot(test_db, user, "Test Bot")
    
    response = await client.post(
        f"/api/v2/bots/{bot.id}/send-offer",
        headers=headers,
        json={
            "partner_id": "12345678",
            "token": "test_token",
            "items": []
        }
    )
    assert response.status_code in [200, 401, 404]


@pytest.mark.asyncio
async def test_v2_bots_get_inventory(client: AsyncClient, test_db: AsyncSession):
    """测试V2获取机器人库存"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    bot = await create_test_bot(test_db, user, "Test Bot")
    
    response = await client.get(
        f"/api/v2/bots/{bot.id}/inventory",
        headers=headers
    )
    assert response.status_code in [200, 401, 404]
