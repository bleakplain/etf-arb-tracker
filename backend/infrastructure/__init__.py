"""
基础设施层 - 提供技术支撑

包括缓存、HTTP客户端、持久化等技术组件
"""

from .cache.ttl_cache import TTLCache, CacheStats, CacheEntry

__all__ = [
    'TTLCache',
    'CacheStats',
    'CacheEntry',
]
