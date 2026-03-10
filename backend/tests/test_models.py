# -*- coding: utf-8 -*-
"""
模型测试
"""
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.bot import Bot
from app.models.monitor import MonitorTask
from app.models.inventory import Inventory
from app.models.order import Order
from app.core.security import verify_password, get_password_hash


@pytest.mark.asyncio
async def test_user_creation(test_db: AsyncSession):
    """测试用户创建"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password123")
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    
    assert user.id is not None
    assert user.username == "testuser"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_password_verification(test_db: AsyncSession):
    """测试密码验证"""
    password = "testpass123"
    hashed = get_password_hash(password)
    
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpass", hashed) is False


@pytest.mark.asyncio
async def test_bot_creation(test_db: AsyncSession):
    """测试机器人创建"""
    user = User(
        username="testuser",
        hashed_password=get_password_hash("password123")
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    
    bot = Bot(
        name="Test Bot",
        steam_id="123456789",
        owner_id=user.id,
        status="offline"
    )
    test_db.add(bot)
    await test_db.commit()
    await test_db.refresh(bot)
    
    assert bot.id is not None
    assert bot.name == "Test Bot"
    assert bot.status == "offline"


@pytest.mark.asyncio
async def test_monitor_task_creation(test_db: AsyncSession):
    """测试监控任务创建"""
    user = User(
        username="testuser",
        hashed_password=get_password_hash("password123")
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    
    monitor = MonitorTask(
        name="Test Monitor",
        condition_type="price_below",
        user_id=user.id,
        enabled=True,
        status="idle"
    )
    test_db.add(monitor)
    await test_db.commit()
    await test_db.refresh(monitor)
    
    assert monitor.id is not None
    assert monitor.name == "Test Monitor"
    assert monitor.enabled is True


@pytest.mark.asyncio
async def test_inventory_creation(test_db: AsyncSession):
    """测试库存创建"""
    user = User(
        username="testuser",
        hashed_password=get_password_hash("password123")
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    
    inventory = Inventory(
        user_id=user.id,
        item_id=1,
        asset_id="123456789",
        status="available"
    )
    test_db.add(inventory)
    await test_db.commit()
    await test_db.refresh(inventory)
    
    assert inventory.id is not None
    assert inventory.status == "available"
