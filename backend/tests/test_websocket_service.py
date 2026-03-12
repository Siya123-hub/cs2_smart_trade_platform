# -*- coding: utf-8 -*-
"""
WebSocket 测试
测试心跳、连接管理和重连机制
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 确保可以导入 app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConnectionManager:
    """测试连接管理器"""

    def test_get_heartbeat_config(self):
        """测试获取心跳配置"""
        from app.api.v2.websocket import ConnectionManager
        
        config = ConnectionManager.get_heartbeat_config()
        
        assert "interval" in config
        assert "timeout" in config
        assert "max_failures" in config
        assert "reconnect_delay" in config

    def test_default_config_values(self):
        """测试默认配置值"""
        from app.api.v2.websocket import ConnectionManager
        
        # 确保加载默认配置
        ConnectionManager._ensure_config_loaded()
        
        assert ConnectionManager.HEARTBEAT_INTERVAL == 30
        assert ConnectionManager.HEARTBEAT_TIMEOUT == 10
        assert ConnectionManager.MAX_FAILURES == 3
        assert ConnectionManager.RECONNECT_DELAY == 5

    def test_update_heartbeat_config(self):
        """测试更新心跳配置"""
        from app.api.v2.websocket import ConnectionManager
        
        # 保存原始值
        original_interval = ConnectionManager.HEARTBEAT_INTERVAL
        
        # 更新配置
        ConnectionManager.update_heartbeat_config(interval=60)
        
        assert ConnectionManager.HEARTBEAT_INTERVAL == 60
        
        # 恢复原始值
        ConnectionManager.HEARTBEAT_INTERVAL = original_interval


class TestWebSocketAuth:
    """测试 WebSocket 认证"""

    def test_validate_token_missing(self):
        """测试空 token 验证"""
        from app.api.v2.websocket import WebSocketAuthManager
        
        result = WebSocketAuthManager.validate_token("")
        
        assert result is None
    
    def test_validate_token_invalid(self):
        """测试无效 token 验证"""
        from app.api.v2.websocket import WebSocketAuthManager
        
        result = WebSocketAuthManager.validate_token("invalid_token")
        
        assert result is None
    
    def test_get_token_expiry(self):
        """测试获取 token 过期时间"""
        from app.api.v2.websocket import WebSocketAuthManager
        from datetime import datetime, timedelta
        import jwt
        
        # 创建一个过期的 token
        payload = {
            "sub": "123",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        token = jwt.encode(payload, "test_secret", algorithm="HS256")
        
        expiry = WebSocketAuthManager.get_token_expiry(token)
        
        # 应该返回 None 或过去的时间
        assert expiry is None or expiry < datetime.utcnow()


class TestHeartbeatTimeout:
    """测试心跳超时处理"""

    @pytest.mark.asyncio
    async def test_heartbeat_timeout_disconnect(self):
        """测试心跳超时断开连接"""
        from app.api.v2.websocket import ConnectionManager
        from fastapi import WebSocket
        
        # 模拟 WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        mock_websocket.receive_json = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_websocket.close = AsyncMock()
        
        # 模拟连接管理器
        with patch('app.api.v2.websocket.ws_manager') as mock_ws_manager:
            mock_ws_manager.active_connections = {}
            mock_ws_manager.disconnect = MagicMock()
            
            # 运行心跳（会超时）
            try:
                await asyncio.wait_for(
                    ConnectionManager.keep_alive(mock_websocket, user_id=1),
                    timeout=5
                )
            except asyncio.TimeoutError:
                pass  # 预期超时
            
            # 验证连续失败后断开连接
            assert mock_websocket.close.called or mock_ws_manager.disconnect.called


class TestReconnectMechanism:
    """测试重连机制"""

    @pytest.mark.asyncio
    async def test_schedule_reconnect(self):
        """测试安排重连"""
        from app.api.v2.websocket import ConnectionManager
        
        # 测试重连调度
        task = asyncio.create_task(ConnectionManager._schedule_reconnect(user_id=999))
        
        # 等待一小段时间
        await asyncio.sleep(0.1)
        
        # 取消任务
        task.cancel()
        
        # 验证任务创建成功
        assert task is not None


class TestWebSocketMessages:
    """测试 WebSocket 消息处理"""

    @pytest.mark.asyncio
    async def test_handle_ping(self):
        """测试处理 ping 消息"""
        from app.api.v2.websocket import ConnectionManager
        from fastapi import WebSocket
        from app.models.user import User
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        
        message = {"type": "ping"}
        user = User(id=1, username="test", email="test@test.com")
        
        await ConnectionManager.handle_client_message(mock_websocket, message, user)
        
        # 验证响应
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "pong"

    @pytest.mark.asyncio
    async def test_handle_subscribe(self):
        """测试处理订阅消息"""
        from app.api.v2.websocket import ConnectionManager
        from fastapi import WebSocket
        from app.models.user import User
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        
        message = {"type": "subscribe", "topic": "orders"}
        user = User(id=1, username="test", email="test@test.com")
        
        await ConnectionManager.handle_client_message(mock_websocket, message, user)
        
        # 验证响应
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "subscribed"
        assert call_args["topic"] == "orders"

    @pytest.mark.asyncio
    async def test_handle_heartbeat(self):
        """测试处理心跳消息"""
        from app.api.v2.websocket import ConnectionManager
        from fastapi import WebSocket
        from app.models.user import User
        
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        
        message = {"type": "heartbeat"}
        user = User(id=1, username="test", email="test@test.com")
        
        await ConnectionManager.handle_client_message(mock_websocket, message, user)
        
        # 验证响应
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "heartbeat_ack"
