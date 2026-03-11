# -*- coding: utf-8 -*-
"""
测试用例 - 交易服务
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.trading_service import TradingEngine, DEFAULT_TIMEOUT
from app.models.item import Item
from app.models.order import Order
from app.models.inventory import Inventory
from app.core.response import ServiceResponse


class TestTradingEngine:
    """交易引擎测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.add = Mock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def mock_buff_client(self):
        """模拟 BUFF 客户端"""
        client = AsyncMock()
        client.get_price_overview = AsyncMock(return_value={
            "lowest_price": "100.00",
            "volume": "100"
        })
        client.create_order = AsyncMock(return_value={
            "result": "success",
            "order_id": "12345"
        })
        return client

    @pytest.fixture
    def mock_item(self):
        """模拟饰品"""
        item = Mock(spec=Item)
        item.id = 1
        item.name = "AK-47 | Redline"
        item.market_hash_name = "AK-47%20Redline"
        item.current_price = 100.0
        item.steam_lowest_price = 120.0
        item.volume_24h = 50
        return item

    @pytest.mark.asyncio
    async def test_get_arbitrage_opportunities(self, mock_db, mock_item):
        """测试获取搬砖机会"""
        # Mock 查询结果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_item]
        mock_db.execute.return_value = mock_result

        engine = TradingEngine(mock_db)
        
        result = await engine.get_arbitrage_opportunities(min_profit=5.0, limit=10)
        
        assert result.success is True
        assert len(result.data) > 0
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_buy_success(self, mock_db, mock_buff_client, mock_item):
        """测试执行买入 - 成功"""
        # Mock 查询结果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        engine = TradingEngine(mock_db)
        engine.set_buff_client("test_cookie")
        engine.buff_client = mock_buff_client
        
        # 替换 get_buff_client
        with patch('app.services.trading_service.get_buff_client', return_value=mock_buff_client):
            result = await engine.execute_buy(
                item_id=1,
                max_price=150.0,
                quantity=1,
                user_id=1,
                timeout=30
            )
        
        # 验证结果
        assert result.success is True
        assert "order_id" in result.data

    @pytest.mark.asyncio
    async def test_execute_buy_price_too_high(self, mock_db, mock_buff_client, mock_item):
        """测试执行买入 - 价格过高"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        engine = TradingEngine(mock_db)
        engine.buff_client = mock_buff_client
        
        with patch('app.services.trading_service.get_buff_client', return_value=mock_buff_client):
            result = await engine.execute_buy(
                item_id=1,
                max_price=50.0,  # 低于当前价格
                quantity=1,
                user_id=1,
                timeout=30
            )
        
        assert result.success is False
        assert result.code == "PRICE_TOO_HIGH"

    @pytest.mark.asyncio
    async def test_execute_buy_no_buff_client(self, mock_db):
        """测试执行买入 - 未设置 BUFF 客户端"""
        engine = TradingEngine(mock_db)
        
        with pytest.raises(Exception, match="未设置 BUFF 客户端"):
            await engine.execute_buy(
                item_id=1,
                max_price=100.0,
                quantity=1,
                user_id=1
            )

    @pytest.mark.asyncio
    async def test_execute_buy_item_not_found(self, mock_db, mock_buff_client):
        """测试执行买入 - 饰品不存在"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        engine = TradingEngine(mock_db)
        engine.buff_client = mock_buff_client
        
        with pytest.raises(Exception, match="饰品不存在"):
            await engine.execute_buy(
                item_id=999,
                max_price=100.0,
                quantity=1,
                user_id=1
            )

    @pytest.mark.asyncio
    async def test_execute_buy_timeout(self, mock_db, mock_buff_client, mock_item):
        """测试执行买入 - 超时"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        # 模拟超时
        async def slow_get_price(*args, **kwargs):
            await asyncio.sleep(60)
            return {"lowest_price": "100.00"}
        
        mock_buff_client.get_price_overview = slow_get_price

        engine = TradingEngine(mock_db)
        engine.buff_client = mock_buff_client
        
        with patch('app.services.trading_service.get_buff_client', return_value=mock_buff_client):
            result = await engine.execute_buy(
                item_id=1,
                max_price=150.0,
                quantity=1,
                user_id=1,
                timeout=1  # 1秒超时
            )
        
        assert result.success is False
        assert result.code == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_execute_arbitrage(self, mock_db, mock_buff_client, mock_item):
        """测试执行搬砖流程"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        engine = TradingEngine(mock_db)
        engine.buff_client = mock_buff_client
        
        with patch('app.services.trading_service.get_buff_client', return_value=mock_buff_client):
            result = await engine.execute_arbitrage(
                item_id=1,
                buy_platform="buff",
                sell_platform="steam"
            )
        
        # 验证买入订单创建
        assert result.success is True

    @pytest.mark.asyncio
    async def test_validate_price(self):
        """测试价格验证"""
        from app.utils.validators import validate_price
        
        # 有效价格
        validate_price(100.0, "test_price")
        validate_price(0.01, "test_price")
        
        # 无效价格
        with pytest.raises(ValueError):
            validate_price(0, "test_price")
        
        with pytest.raises(ValueError):
            validate_price(-10.0, "test_price")

    @pytest.mark.asyncio
    async def test_validate_quantity(self):
        """测试数量验证"""
        from app.utils.validators import validate_quantity
        
        # 有效数量
        validate_quantity(1)
        validate_quantity(100)
        
        # 无效数量
        with pytest.raises(ValueError):
            validate_quantity(0)
        
        with pytest.raises(ValueError):
            validate_quantity(-1)
        
        with pytest.raises(ValueError):
            validate_quantity(1000)  # 超过最大限制

    @pytest.mark.asyncio
    async def test_validate_min_profit(self):
        """测试最小利润验证"""
        from app.utils.validators import validate_min_profit
        
        # 有效利润
        validate_min_profit(0)
        validate_min_profit(100.0)
        
        # 无效利润
        with pytest.raises(ValueError):
            validate_min_profit(-1.0)

    @pytest.mark.asyncio
    async def test_default_timeout_value(self):
        """测试默认超时配置"""
        assert DEFAULT_TIMEOUT == 30


class TestArbitrageCalculation:
    """搬砖计算测试"""

    @pytest.mark.asyncio
    async def test_profit_calculation(self):
        """测试利润计算"""
        buff_price = 100.0
        steam_price = 120.0
        
        # Steam 出售需要 15% 手续费
        steam_sell_price = steam_price * 0.85
        profit = steam_sell_price - buff_price
        
        assert profit == 2.0  # 120 * 0.85 - 100 = 2

    @pytest.mark.asyncio
    async def test_profit_percent_calculation(self):
        """测试利润百分比计算"""
        buff_price = 100.0
        steam_price = 120.0
        
        steam_sell_price = steam_price * 0.85
        profit = steam_sell_price - buff_price
        profit_percent = (profit / buff_price * 100) if buff_price > 0 else 0
        
        assert profit_percent == 2.0

    @pytest.mark.asyncio
    async def test_no_profit_scenario(self):
        """测试无利润场景"""
        buff_price = 100.0
        steam_price = 100.0
        
        steam_sell_price = steam_price * 0.85
        profit = steam_sell_price - buff_price
        
        assert profit < 0  # 亏损

    @pytest.mark.asyncio
    async def test_high_profit_scenario(self):
        """测试高利润场景"""
        buff_price = 50.0
        steam_price = 100.0
        
        steam_sell_price = steam_price * 0.85
        profit = steam_sell_price - buff_price
        
        assert profit == 35.0  # 100 * 0.85 - 50 = 35
        assert profit / buff_price * 100 == 70.0  # 70% 利润
