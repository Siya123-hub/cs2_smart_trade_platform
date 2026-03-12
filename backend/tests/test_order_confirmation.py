# -*- coding: utf-8 -*-
"""
订单确认服务单元测试
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.order_confirmation import (
    OrderConfirmationService,
    OrderConfirmationStatus,
)


class TestOrderConfirmationService:
    """订单确认服务测试"""
    
    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db
    
    @pytest.fixture
    def confirmation_service(self, mock_db):
        """创建订单确认服务实例"""
        return OrderConfirmationService(mock_db)
    
    @pytest.mark.asyncio
    async def test_confirm_order_success(self, confirmation_service, mock_db):
        """测试订单确认成功"""
        # 模拟本地订单状态已确认
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            order_id="TEST-001",
            status="completed"
        )
        mock_db.execute.return_value = mock_result
        
        result = await confirmation_service.confirm_order(
            order_id="TEST-001",
            external_order_id="EXT-001",
            source="local",
            timeout=5,
            check_interval=1
        )
        
        assert result["order_id"] == "TEST-001"
        assert result["confirmed"] is True
    
    @pytest.mark.asyncio
    async def test_confirm_order_timeout(self, confirmation_service, mock_db):
        """测试订单确认超时"""
        # 模拟订单状态一直未确认
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            order_id="TEST-002",
            status="pending"
        )
        mock_db.execute.return_value = mock_result
        
        result = await confirmation_service.confirm_order(
            order_id="TEST-002",
            external_order_id="EXT-002",
            source="local",
            timeout=2,  # 短超时
            check_interval=1
        )
        
        assert result["order_id"] == "TEST-002"
        assert result["status"] == OrderConfirmationStatus.TIMEOUT
        assert result["confirmed"] is False
    
    @pytest.mark.asyncio
    async def test_get_confirmation_status_pending(self, confirmation_service, mock_db):
        """测试获取进行中的确认状态"""
        # 创建后台确认任务
        confirmation_service._pending_confirmations["TEST-003"] = asyncio.create_task(
            asyncio.sleep(10)  # 模拟长时间运行的任务
        )
        
        result = await confirmation_service.get_confirmation_status("TEST-003")
        
        assert result["status"] == OrderConfirmationStatus.CONFIRMING
        assert result["confirmed"] is False
    
    @pytest.mark.asyncio
    async def test_get_confirmation_status_completed(self, confirmation_service, mock_db):
        """测试获取已完成的确认状态"""
        # 设置已完成的结果
        confirmation_service._confirmation_results["TEST-004"] = {
            "order_id": "TEST-004",
            "status": OrderConfirmationStatus.CONFIRMED,
            "confirmed": True
        }
        
        result = await confirmation_service.get_confirmation_status("TEST-004")
        
        assert result["status"] == OrderConfirmationStatus.CONFIRMED
        assert result["confirmed"] is True
    
    @pytest.mark.asyncio
    async def test_cancel_confirmation(self, confirmation_service):
        """测试取消订单确认"""
        # 创建一个可取消的任务
        task = asyncio.create_task(asyncio.sleep(10))
        confirmation_service._pending_confirmations["TEST-005"] = task
        
        result = await confirmation_service.cancel_confirmation("TEST-005")
        
        assert result is True
        assert "TEST-005" not in confirmation_service._pending_confirmations
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_confirmation(self, confirmation_service):
        """测试取消不存在的确认"""
        result = await confirmation_service.cancel_confirmation("NONEXISTENT")
        
        assert result is False


class TestOrderConfirmationStatus:
    """订单确认状态常量测试"""
    
    def test_status_constants(self):
        """测试状态常量定义"""
        assert OrderConfirmationStatus.PENDING == "pending"
        assert OrderConfirmationStatus.CONFIRMING == "confirming"
        assert OrderConfirmationStatus.CONFIRMED == "confirmed"
        assert OrderConfirmationStatus.FAILED == "failed"
        assert OrderConfirmationStatus.CANCELLED == "cancelled"
        assert OrderConfirmationStatus.TIMEOUT == "timeout"
