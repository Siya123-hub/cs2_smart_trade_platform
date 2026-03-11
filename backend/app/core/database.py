# -*- coding: utf-8 -*-
"""
数据库连接配置
"""
import sqlite3
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event, text
from sqlalchemy.pool import StaticPool

from app.core.config import settings


# 判断是否为 SQLite 数据库
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if is_sqlite:
    # SQLite 配置优化
    # 转换为aiosqlite兼容的URL
    db_url = settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    
    engine = create_async_engine(
        db_url,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        pool_pre_ping=True,
    )
    
    # 配置 SQLite WAL 模式和 busy_timeout
    async def configure_sqlite(engine):
        """配置 SQLite 优化参数"""
        async with engine.begin() as conn:
            # 启用 WAL 模式（提高并发性能）
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            # 设置 busy_timeout（等待锁释放的时间）
            await conn.execute(text("PRAGMA busy_timeout=30000"))
            # 启用外键约束
            await conn.execute(text("PRAGMA foreign_keys=ON"))
            # 同步模式设为 NORMAL（WAL模式下推荐）
            await conn.execute(text("PRAGMA synchronous=NORMAL"))
            # 设置缓存大小（负数表示KB）
            await conn.execute(text("PRAGMA cache_size=-2000"))
            # 启用内存模式共享
            await conn.execute(text("PRAGMA mmap_size=268435456"))
    
    # 应用 SQLite 配置
    import asyncio
    asyncio.get_event_loop().run_until_complete(configure_sqlite(engine))
else:
    # PostgreSQL/MySQL 配置
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_timeout=30,
    )

# 创建会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 创建基类
Base = declarative_base()


async def get_db() -> AsyncSession:
    """获取数据库会话依赖"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
