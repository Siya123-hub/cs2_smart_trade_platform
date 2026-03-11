#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CS2 智能交易平台 - 命令行工具

用法:
    python -m app.cli init_db              # 初始化数据库
    python -m app.cli create_admin          # 创建管理员账户
    python -m app.cli test_api              # 测试 API 连接
    python -m app.cli reset_cache           # 重置缓存
"""
import asyncio
import sys
import os
from typing import Optional

import click
from sqlalchemy import text

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import engine, async_session_factory, Base
from app.core.security import get_password_hash
from app.models.user import User
from app.models.bot import Bot
from app.models.order import Order
from app.models.inventory import Inventory
from app.models.monitor import MonitorTask


@click.group()
def cli():
    """CS2 智能交易平台 - CLI 工具"""
    pass


@cli.command()
def init_db():
    """初始化数据库 - 创建所有表"""
    click.echo("正在初始化数据库...")
    
    async def _init_db():
        async with engine.begin() as conn:
            # 创建所有表
            await conn.run_sync(Base.metadata.create_all)
            click.echo("✓ 所有表已创建")
        
        # 验证表是否创建成功
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            click.echo(f"✓ 数据库包含 {len(tables)} 个表:")
            for table in tables:
                click.echo(f"  - {table}")
    
    asyncio.run(_init_db())
    click.echo("✓ 数据库初始化完成")


@cli.command()
@click.option('--username', '-u', prompt=True, help='管理员用户名')
@click.option('--email', '-e', prompt=True, help='管理员邮箱')
@click.option('--password', '-p', prompt=True, hide_input=True, confirmation_prompt=True, help='管理员密码')
def create_admin(username: str, email: str, password: str):
    """创建管理员账户"""
    click.echo(f"正在创建管理员账户: {username}")
    
    async def _create_admin():
        async with async_session_factory() as session:
            # 检查用户是否已存在
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.username == username)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                click.echo(f"✗ 用户 {username} 已存在", err=True)
                return
            
            # 创建管理员
            admin = User(
                username=username,
                email=email,
                hashed_password=get_password_hash(password),
                is_active=True,
                is_superuser=True,
                is_verified=True
            )
            
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            
            click.echo(f"✓ 管理员账户创建成功 (ID: {admin.id})")
            click.echo(f"  用户名: {username}")
            click.echo(f"  邮箱: {email}")
            click.echo(f"  权限: 超级管理员")
    
    asyncio.run(_create_admin())


@cli.command()
def test_api():
    """测试 API 连接"""
    click.echo("正在测试 API 连接...")
    
    async def _test_api():
        # 测试数据库连接
        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
            click.echo("✓ 数据库连接正常")
        except Exception as e:
            click.echo(f"✗ 数据库连接失败: {e}", err=True)
        
        # 测试 Redis 连接
        try:
            import redis.asyncio as redis
            r = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
            await r.ping()
            await r.close()
            click.echo("✓ Redis 连接正常")
        except Exception as e:
            click.echo(f"✗ Redis 连接失败: {e}", err=True)
        
        # 显示配置信息
        click.echo("\n当前配置:")
        click.echo(f"  数据库: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
        click.echo(f"  Redis: {settings.REDIS_URL.split('@')[-1] if '@' in settings.REDIS_URL else settings.REDIS_URL}")
        click.echo(f"  调试模式: {settings.DEBUG}")
    
    asyncio.run(_test_api())


@cli.command()
@click.confirmation_option(prompt='确定要重置所有缓存吗?')
def reset_cache():
    """重置所有缓存"""
    click.echo("正在重置缓存...")
    
    async def _reset_cache():
        try:
            import redis.asyncio as redis
            r = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
            
            # 刷新数据库
            await r.flushdb()
            await r.close()
            
            click.echo("✓ 缓存已重置")
        except Exception as e:
            click.echo(f"✗ 缓存重置失败: {e}", err=True)
    
    asyncio.run(_reset_cache())


@cli.command()
@click.option('--username', '-u', help='用户名（可选，查看特定用户统计）')
def stats(username: Optional[str]):
    """查看系统统计信息"""
    click.echo("正在获取统计信息...")
    
    async def _stats():
        async with async_session_factory() as session:
            from sqlalchemy import select, func
            
            # 用户数
            user_count = await session.scalar(select(func.count(User.id)))
            
            # 机器人总数
            bot_count = await session.scalar(select(func.count(Bot.id)))
            
            # 订单总数
            order_count = await session.scalar(select(func.count(Order.id)))
            
            # 库存数量
            inventory_count = await session.scalar(select(func.count(Inventory.id)))
            
            # 监控任务数
            monitor_count = await session.scalar(select(func.count(MonitorTask.id)))
            
            click.echo("\n系统统计:")
            click.echo(f"  用户总数: {user_count or 0}")
            click.echo(f"  机器人总数: {bot_count or 0}")
            click.echo(f"  订单总数: {order_count or 0}")
            click.echo(f"  库存数量: {inventory_count or 0}")
            click.echo(f"  监控任务: {monitor_count or 0}")
    
    asyncio.run(_stats())


@cli.command()
@click.option('--username', '-u', prompt=True, help='用户名')
@click.option('--password', '-p', prompt=True, hide_input=True, help='密码')
def login(username: str, password: str):
    """测试登录功能"""
    click.echo(f"正在测试登录: {username}")
    
    async def _login():
        async with async_session_factory() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                click.echo("✗ 用户不存在", err=True)
                return
            
            if not user.is_active:
                click.echo("✗ 账户已被禁用", err=True)
                return
            
            from app.core.security import verify_password
            if not verify_password(password, user.hashed_password):
                click.echo("✗ 密码错误", err=True)
                return
            
            click.echo("✓ 登录成功")
            click.echo(f"  用户名: {user.username}")
            click.echo(f"  邮箱: {user.email}")
            click.echo(f"  超级管理员: {user.is_superuser}")
    
    asyncio.run(_login())


@cli.command()
@click.confirmation_option(prompt='确定要删除所有数据吗? 此操作不可恢复!')
def drop_all():
    """删除所有数据库表"""
    click.echo("正在删除所有表...")
    
    async def _drop_all():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        click.echo("✓ 所有表已删除")
    
    asyncio.run(_drop_all())


if __name__ == '__main__':
    cli()
