# -*- coding: utf-8 -*-
"""
缓存服务 - 内存缓存实现（带 TTL）
"""
import time
from typing import Any, Dict, Optional
from threading import Lock


class CacheEntry:
    """缓存条目"""
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expire_at = time.time() + ttl if ttl > 0 else float('inf')
    
    def is_expired(self) -> bool:
        return time.time() > self.expire_at


class MemoryCache:
    """
    简单的内存缓存实现
    
    特性:
    - 支持 TTL（生存时间）
    - 线程安全
    - 自动清理过期条目
    """
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        # 统计信息
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            default: 不存在时返回的默认值
            
        Returns:
            缓存值，如果不存在或已过期返回 default
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return default
            
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），默认 300 秒（5 分钟）
        """
        with self._lock:
            self._cache[key] = CacheEntry(value, ttl)
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def cleanup_expired(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的条目数量
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total,
                "hit_rate": round(hit_rate, 2),
                "total_keys": len(self._cache),
            }
    
    def keys(self) -> list:
        """获取所有缓存键"""
        with self._lock:
            return list(self._cache.keys())


# 全局缓存实例
_cache = MemoryCache()


# ============ 便捷函数 ============

def get_cache() -> MemoryCache:
    """获取全局缓存实例"""
    return _cache


def get(key: str, default: Any = None) -> Any:
    """获取缓存值"""
    value = _cache.get(key)
    return value if value is not None else default


def set(key: str, value: Any, ttl: int = 300) -> None:
    """设置缓存值"""
    _cache.set(key, value, ttl)


def delete(key: str) -> bool:
    """删除缓存"""
    return _cache.delete(key)


def clear() -> None:
    """清空缓存"""
    _cache.clear()


def get_stats() -> Dict[str, Any]:
    """获取缓存统计"""
    return _cache.get_stats()


# ============ 特定用途的缓存函数 ============

# 热门物品缓存
ITEMS_CACHE_TTL = 600  # 10 分钟
ITEMS_CACHE_KEY = "popular_items"

# 价格数据缓存
PRICE_CACHE_TTL = 300  # 5 分钟
PRICE_CACHE_PREFIX = "price:"


def get_popular_items() -> Optional[Any]:
    """获取热门物品缓存"""
    return _cache.get(ITEMS_CACHE_KEY)


def set_popular_items(items: list, ttl: int = ITEMS_CACHE_TTL) -> None:
    """设置热门物品缓存"""
    _cache.set(ITEMS_CACHE_KEY, items, ttl)


def get_cached_price(item_id: str) -> Optional[Any]:
    """获取物品价格缓存"""
    return _cache.get(f"{PRICE_CACHE_PREFIX}{item_id}")


def set_cached_price(item_id: str, price: Any, ttl: int = PRICE_CACHE_TTL) -> None:
    """设置物品价格缓存"""
    _cache.set(f"{PRICE_CACHE_PREFIX}{item_id}", price, ttl)
