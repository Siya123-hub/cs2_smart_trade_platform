# -*- coding: utf-8 -*-
"""
配置管理单元测试
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSettings:
    """配置类测试"""
    
    def test_default_values(self):
        """测试默认配置值"""
        from app.core.config import Settings
        
        settings = Settings()
        
        assert settings.APP_NAME == "CS2 Trade Platform"
        assert settings.DEBUG is False
        assert settings.STEAM_APP_ID == 730
        assert settings.STEAM_CONTEXT_ID == 2
    
    def test_custom_values(self):
        """测试自定义配置值"""
        from app.core.config import Settings
        
        settings = Settings(
            APP_NAME="Test App",
            DEBUG=True,
            STEAM_APP_ID=730,
            MAX_SINGLE_TRADE=5000
        )
        
        assert settings.APP_NAME == "Test App"
        assert settings.DEBUG is True
        assert settings.MAX_SINGLE_TRADE == 5000
    
    def test_websocket_config(self):
        """测试WebSocket配置"""
        from app.core.config import Settings
        
        settings = Settings()
        
        assert settings.WS_HEARTBEAT_INTERVAL == 30
        assert settings.WS_HEARTBEAT_TIMEOUT == 10
        assert settings.WS_MAX_FAILURES == 3
        assert settings.WS_RECONNECT_DELAY == 5
        assert settings.WS_TOKEN_EXPIRY_WARNING == 300
    
    def test_database_config(self):
        """测试数据库配置"""
        from app.core.config import Settings
        
        settings = Settings()
        
        assert settings.DB_BUSY_TIMEOUT == 30000
        assert settings.DB_POOL_RECYCLE == 3600
        assert settings.DB_POOL_TIMEOUT == 30
    
    def test_order_confirmation_config(self):
        """测试订单确认配置"""
        from app.core.config import Settings
        
        settings = Settings()
        
        assert settings.ORDER_CONFIRM_CHECK_INTERVAL == 5
        assert settings.ORDER_CONFIRM_TIMEOUT == 300
        assert settings.ORDER_POLL_RETRIES == 10
    
    def test_rate_limit_config(self):
        """测试限流配置"""
        from app.core.config import Settings
        
        settings = Settings()
        
        assert settings.RATE_LIMIT_ENABLED is True
        assert settings.RATE_LIMIT_DEFAULT_REQUESTS == 60
        assert settings.RATE_LIMIT_DEFAULT_WINDOW == 60
        assert settings.RATE_LIMIT_DEFAULT_BURST == 10
    
    def test_steam_config(self):
        """测试Steam配置"""
        from app.core.config import Settings
        
        settings = Settings()
        
        assert settings.STEAM_APP_ID == 730
        assert settings.STEAM_CONTEXT_ID == 2
    
    def test_trading_limits(self):
        """测试交易限额配置"""
        from app.core.config import Settings
        
        settings = Settings()
        
        assert settings.MIN_PROFIT == 1.0
        assert settings.MAX_SINGLE_TRADE == 10000
    
    def test_cache_config(self):
        """测试缓存配置"""
        from app.core.config import Settings
        
        settings = Settings()
        
        assert settings.PRICE_UPDATE_INTERVAL_HIGH == 5
        assert settings.PRICE_UPDATE_INTERVAL_MEDIUM == 30
        assert settings.PRICE_UPDATE_INTERVAL_LOW == 300
        assert settings.CACHE_CLEANUP_INTERVAL == 300
        assert settings.RESPONSE_TIME_TTL == 300


class TestSettingsValidation:
    """配置验证测试"""
    
    @patch.dict('os.environ', {'SECRET_KEY': '', 'ENCRYPTION_KEY': 'test_key'})
    def test_prod_requires_secret_key(self):
        """测试生产环境需要密钥"""
        from app.core.config import Settings
        
        with pytest.raises(ValueError):
            Settings(DEBUG=False)
    
    def test_warning_without_encryption_key(self):
        """测试未设置加密密钥时发出警告"""
        from app.core.config import Settings
        import warnings
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Settings(DEBUG=True, SECRET_KEY="test", ENCRYPTION_KEY="")
            
            # 应该发出警告
            assert len(w) > 0


class TestGetSettings:
    """获取配置单例测试"""
    
    def test_get_settings_returns_same_instance(self):
        """测试get_settings返回同一实例"""
        from app.core.config import get_settings
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
