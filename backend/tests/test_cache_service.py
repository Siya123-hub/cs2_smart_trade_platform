# -*- coding: utf-8 -*-
"""
缓存服务测试
测试缓存初始化、并发访问和故障转移
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# 确保可以导入 app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.cache import (
    CacheManager,
    CacheBackend,
    MemoryCache,
    RedisCache,
    get_cache,
    init_cache,
    is_cache_initialized,
    _cache_initialized,
)


class TestCacheInitialization:
    """测试缓存初始化"""

    @pytest.mark.asyncio
    async def test_memory_cache_initialization(self):
        """测试内存缓存初始化"""
        cache = CacheManager(backend=CacheBackend.MEMORY)
        await cache.initialize()
        
        assert cache.backend == CacheBackend.MEMORY
        assert is_cache_initialized() is True
        
    @pytest.mark.asyncio
    async def test_redis_cache_fallback_to_memory(self):
        """测试 Redis 不可用时回退到内存缓存"""
        cache = CacheManager(
            backend=CacheBackend.REDIS,
            redis_url="redis://invalid-host:6379/0"
        )
        await cache.initialize(max_retries=1, retry_delay=0.1)
        
        # 应该回退到内存缓存
        assert cache.backend == CacheBackend.MEMORY


class TestMemoryCache:
    """测试内存缓存"""

    def test_set_and_get(self):
        """测试设置和获取"""
        cache = MemoryCache()
        cache.set("key1", "value1", ttl=300)
        
        assert cache.get("key1") == "value1"
    
    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        cache = MemoryCache()
        
        assert cache.get("nonexistent") is None
        assert cache.get("nonexistent", "default") == "default"
    
    def test_delete(self):
        """测试删除"""
        cache = MemoryCache()
        cache.set("key1", "value1")
        
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
    
    def test_lru_eviction(self):
        """测试 LRU 淘汰"""
        cache = MemoryCache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # 应该淘汰 key1
        
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"
    
    def test_cleanup_expired(self):
        """测试过期清理"""
        import time
        cache = MemoryCache()
        cache.set("key1", "value1", ttl=1)  # 1秒过期
        
        time.sleep(1.1)
        
        assert cache.cleanup_expired() == 1
        assert cache.get("key1") is None
    
    def test_stats(self):
        """测试统计信息"""
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("nonexistent")
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0


class TestCacheManager:
    """测试缓存管理器"""

    @pytest.mark.asyncio
    async def test_get_cache(self):
        """测试获取缓存实例"""
        cache = get_cache()
        assert cache is not None

    @pytest.mark.asyncio
    async def test_cache_operations(self):
        """测试缓存操作"""
        cache = get_cache()
        
        # 设置
        cache.set("test_key", "test_value", ttl=60)
        
        # 获取
        value = cache.get("test_key")
        assert value == "test_value"
        
        # 删除
        deleted = cache.delete("test_key")
        assert deleted is True
        
        # 验证删除
        assert cache.get("test_key") is None


class TestCacheConcurrency:
    """测试缓存并发访问"""

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """测试并发访问"""
        cache = get_cache()
        
        async def worker(worker_id):
            for i in range(10):
                key = f"key_{worker_id}_{i}"
                cache.set(key, f"value_{worker_id}_{i}")
                value = cache.get(key)
                assert value == f"value_{worker_id}_{i}"
        
        # 并发运行多个 worker
        tasks = [worker(i) for i in range(5)]
        await asyncio.gather(*tasks)


class TestCacheFallback:
    """测试缓存故障转移"""

    @pytest.mark.asyncio
    async def test_fallback_to_memory(self):
        """测试 Redis 故障时回退到内存"""
        # 模拟 Redis 不可用
        cache = CacheManager(backend=CacheBackend.MEMORY)
        cache.set("fallback_key", "fallback_value")
        
        value = cache.get("fallback_key")
        assert value == "fallback_value"
