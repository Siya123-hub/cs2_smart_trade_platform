# -*- coding: utf-8 -*-
"""
测试配置
"""
import pytest
import asyncio
import os
import sys
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import StaticPool
import pytest_asyncio

# 设置环境变量在导入app之前
os.environ["DEBUG"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "true"
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-change-in-production"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-for-testing-only"


# 测试数据库 URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
def event_loop():
    """创建事件循环 - 每个测试函数使用独立的循环"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis 客户端"""
    mock = AsyncMock()
    # 模拟 Redis 基本操作
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.expire = AsyncMock(return_value=1)
    mock.ttl = AsyncMock(return_value=60)
    mock.zadd = AsyncMock(return_value=1)
    mock.zremrangebyscore = AsyncMock(return_value=0)
    mock.zcard = AsyncMock(return_value=0)
    mock.zscore = AsyncMock(return_value=None)
    mock.sadd = AsyncMock(return_value=1)
    mock.smembers = AsyncMock(return_value=set())
    mock.srem = AsyncMock(return_value=1)
    mock.publish = AsyncMock(return_value=1)
    mock.ping = AsyncMock(return_value=True)
    mock.close = AsyncMock()
    return mock


@pytest.fixture(autouse=True)
def patch_redis(mock_redis):
    """自动 mock 所有 Redis 连接"""
    with patch('redis.asyncio.Redis', return_value=mock_redis):
        with patch('redis.Redis', return_value=mock_redis):
            yield mock_redis


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """测试数据库"""
    from app.core.database import Base
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = AsyncSession(engine, expire_on_commit=False)
    
    yield async_session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """测试客户端"""
    from app.main import app
    from app.core.database import get_db
    
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()
