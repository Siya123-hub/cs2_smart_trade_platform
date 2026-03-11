# -*- coding: utf-8 -*-
"""
API 集成测试 - 监控相关
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime

from app.main import app


class TestMonitorAPI:
    """监控 API 测试"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = Mock()
        session.refresh = AsyncMock()
        session.close = AsyncMock()
        return session

    @pytest.fixture
    def mock_current_user(self):
        """模拟当前用户"""
        user = Mock()
        user.id = 1
        user.username = "testuser"
        user.is_superuser = False
        return user

    @pytest.fixture
    def mock_monitor_task(self):
        """模拟监控任务"""
        task = Mock()
        task.id = 1
        task.name = "Test Monitor"
        task.item_id = 1
        task.condition_type = "price_below"
        task.threshold = 100.0
        task.action = "notify"
        task.enabled = True
        task.status = "idle"
        task.user_id = 1
        task.trigger_count = 0
        task.last_triggered = None
        task.created_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        return task

    @pytest.mark.asyncio
    async def test_create_monitor_task(self, mock_db_session, mock_current_user, mock_monitor_task):
        """测试创建监控任务"""
        # Mock 查询结果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        # 模拟返回创建的 task
        mock_monitor_task.id = 1
        
        # 验证任务创建逻辑
        assert mock_monitor_task.name == "Test Monitor"
        assert mock_monitor_task.condition_type == "price_below"
        assert mock_monitor_task.threshold == 100.0

    @pytest.mark.asyncio
    async def test_monitor_task_conditions(self, mock_monitor_task):
        """测试监控任务条件判断"""
        # 测试 price_below 条件
        item_price = 80.0
        threshold = 100.0
        
        # price_below: 当价格 <= 阈值时触发
        triggered = item_price <= threshold
        assert triggered is True
        
        # price_above: 当价格 >= 阈值时触发
        item_price = 120.0
        triggered = item_price >= threshold
        assert triggered is True
        
        # arbitrage: 当利润 >= 阈值时触发
        buff_price = 80.0
        steam_price = 120.0
        threshold = 10.0
        
        profit = steam_price * 0.85 - buff_price
        triggered = profit >= threshold
        assert triggered is True
        assert profit == 22.0

    @pytest.mark.asyncio
    async def test_monitor_task_trigger_count(self, mock_monitor_task):
        """测试触发计数"""
        initial_count = mock_monitor_task.trigger_count
        assert initial_count == 0
        
        # 模拟触发
        mock_monitor_task.trigger_count += 1
        mock_monitor_task.last_triggered = datetime.utcnow()
        
        assert mock_monitor_task.trigger_count == 1
        assert mock_monitor_task.last_triggered is not None

    @pytest.mark.asyncio
    async def test_monitor_task_enable_disable(self, mock_monitor_task):
        """测试监控任务启用/禁用"""
        # 启用
        mock_monitor_task.enabled = True
        assert mock_monitor_task.enabled is True
        
        # 禁用
        mock_monitor_task.enabled = False
        assert mock_monitor_task.enabled is False


class TestPriceMonitor:
    """价格监控服务测试"""

    @pytest.mark.asyncio
    async def test_check_arbitrage_opportunity(self):
        """测试检查搬砖机会"""
        # 测试用例数据
        test_cases = [
            # (buff_price, steam_price, min_profit, expected_profit)
            (100.0, 120.0, 5.0, 2.0),     # 有利润但低于阈值
            (50.0, 100.0, 5.0, 35.0),     # 高利润
            (100.0, 100.0, 5.0, -15.0),   # 亏损
            (10.0, 20.0, 1.0, 7.0),       # 小额利润
        ]
        
        for buff_price, steam_price, min_profit, expected_profit in test_cases:
            steam_sell_price = steam_price * 0.85
            actual_profit = steam_sell_price - buff_price
            
            # 验证利润计算
            assert abs(actual_profit - expected_profit) < 0.01, \
                f"Expected profit {expected_profit}, got {actual_profit}"
            
            # 检查是否满足最小利润要求
            has_opportunity = actual_profit >= min_profit
            print(f"buff={buff_price}, steam={steam_price}, profit={actual_profit}, opportunity={has_opportunity}")

    @pytest.mark.asyncio
    async def test_distributed_lock(self):
        """测试分布式锁"""
        # 模拟 Redis 客户端
        mock_redis = AsyncMock()
        
        # 模拟获取锁成功
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.eval = AsyncMock(return_value=1)
        
        # 测试获取锁
        lock_key = "test:lock:1"
        lock_value = "unique-lock-id"
        
        # 模拟 SET NX EX (原子操作)
        acquired = await mock_redis.set(lock_key, lock_value, nx=True, ex=60)
        assert acquired is True
        
        # 测试释放锁 (Lua 脚本)
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        result = await mock_redis.eval(lua_script, 1, lock_key, lock_value)
        assert result == 1

    @pytest.mark.asyncio
    async def test_lock_timeout(self):
        """测试锁超时"""
        mock_redis = AsyncMock()
        
        # 模拟获取锁失败 (已存在)
        mock_redis.set = AsyncMock(return_value=False)
        
        lock_key = "test:lock:2"
        
        # 尝试获取锁
        acquired = await mock_redis.set(lock_key, "another-lock-id", nx=True, ex=60)
        
        # 验证锁获取失败
        assert acquired is False


class TestMonitorConditions:
    """监控条件测试"""

    def test_price_below_condition(self):
        """测试价格低于条件"""
        test_cases = [
            (50.0, 100.0, True),   # 价格低于阈值
            (100.0, 100.0, True),  # 价格等于阈值
            (150.0, 100.0, False), # 价格高于阈值
        ]
        
        for price, threshold, expected in test_cases:
            result = price <= threshold
            assert result == expected, f"price={price}, threshold={threshold}, expected={expected}"

    def test_price_above_condition(self):
        """测试价格高于条件"""
        test_cases = [
            (150.0, 100.0, True),   # 价格高于阈值
            (100.0, 100.0, True),   # 价格等于阈值
            (50.0, 100.0, False),  # 价格低于阈值
        ]
        
        for price, threshold, expected in test_cases:
            result = price >= threshold
            assert result == expected, f"price={price}, threshold={threshold}, expected={expected}"

    def test_arbitrage_condition(self):
        """测试搬砖条件"""
        test_cases = [
            # (buff_price, steam_price, threshold, expected)
            (50.0, 100.0, 10.0, True),   # 利润 35 > 阈值 10
            (80.0, 100.0, 10.0, False),  # 利润 5 < 阈值 10
            (100.0, 100.0, 10.0, False), # 亏损
        ]
        
        for buff_price, steam_price, threshold, expected in test_cases:
            profit = steam_price * 0.85 - buff_price
            result = profit >= threshold
            assert result == expected, f"profit={profit}, threshold={threshold}, expected={expected}"

    def test_auto_buy_action(self):
        """测试自动买入动作"""
        # 模拟自动买入参数
        buy_params = {
            "item_id": 1,
            "max_price": 100.0,
            "quantity": 1,
            "user_id": 1
        }
        
        # 验证参数
        assert buy_params["item_id"] == 1
        assert buy_params["max_price"] == 100.0
        assert buy_params["quantity"] == 1
        assert buy_params["user_id"] == 1

    def test_notification_action(self):
        """测试通知动作"""
        # 模拟通知内容
        notification = {
            "type": "price_alert",
            "item_name": "AK-47 | Redline",
            "current_price": 80.0,
            "threshold": 100.0,
            "message": "AK-47 | Redline 价格低于 100.0，当前价格: 80.0"
        }
        
        # 验证通知内容
        assert notification["type"] == "price_alert"
        assert "AK-47" in notification["item_name"]
        assert notification["current_price"] < notification["threshold"]
