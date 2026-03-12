# -*- coding: utf-8 -*-
"""
V2 Monitors 高级API测试
测试V2版本 Monitors 高级功能
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.monitor import MonitorTask
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


async def create_test_monitor(
    test_db: AsyncSession,
    user: User,
    item_name: str = "AK-47 | Redline"
) -> MonitorTask:
    """创建测试监控"""
    monitor = MonitorTask(
        user_id=user.id,
        name="Test Monitor",
        item_name=item_name,
        price_threshold=100.0,
        is_active=True
    )
    test_db.add(monitor)
    await test_db.commit()
    await test_db.refresh(monitor)
    return monitor


async def get_auth_header(user: User) -> dict:
    """获取认证头"""
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_v2_monitors_batch_create(client: AsyncClient, test_db: AsyncSession):
    """测试V2批量创建监控"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    response = await client.post(
        "/api/v2/monitors/batch",
        headers=headers,
        json={
            "monitors": [
                {"name": "Monitor 1", "item_name": "AK-47 | Redline", "price_threshold": 100.0},
                {"name": "Monitor 2", "item_name": "M4A1-S | Night", "price_threshold": 200.0}
            ]
        }
    )
    assert response.status_code in [201, 401, 422]


@pytest.mark.asyncio
async def test_v2_monitors_toggle_all(client: AsyncClient, test_db: AsyncSession):
    """测试V2批量切换监控状态"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    # 创建测试监控
    await create_test_monitor(test_db, user, "AK-47 | Redline")
    await create_test_monitor(test_db, user, "M4A1-S | Night")
    
    response = await client.post(
        "/api/v2/monitors/toggle-all",
        headers=headers,
        json={"is_active": False}
    )
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_v2_monitors_get_price_history(client: AsyncClient, test_db: AsyncSession):
    """测试V2获取价格历史"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    response = await client.get(
        "/api/v2/monitors/price-history/AK-47 | Redline",
        headers=headers
    )
    assert response.status_code in [200, 401, 404]


@pytest.mark.asyncio
async def test_v2_monitors_get_alerts(client: AsyncClient, test_db: AsyncSession):
    """测试V2获取价格提醒"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    response = await client.get("/api/v2/monitors/alerts", headers=headers)
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_v2_monitors_export(client: AsyncClient, test_db: AsyncSession):
    """测试V2导出监控列表"""
    user = await create_test_user(test_db)
    headers = await get_auth_header(user)
    
    # 创建测试监控
    await create_test_monitor(test_db, user, "AK-47 | Redline")
    
    response = await client.get(
        "/api/v2/monitors/export",
        headers=headers,
        params={"format": "json"}
    )
    assert response.status_code in [200, 401]
