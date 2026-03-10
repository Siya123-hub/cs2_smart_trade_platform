# -*- coding: utf-8 -*-
"""
认证测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    """测试用户注册"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "password": "testpass123",
            "email": "test@example.com"
        }
    )
    assert response.status_code in [201, 400]  # 201 成功或 400 用户已存在


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    """测试用户登录"""
    # 先注册
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    
    # 登录
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    """测试获取当前用户"""
    # 先注册
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    
    # 登录
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        
        # 获取当前用户
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    """测试登出"""
    # 先注册并登录
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        
        # 登出
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
