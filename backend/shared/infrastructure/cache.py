"""
TTL缓存组件 - 可复用的带过期时间的缓存

消除重复的缓存逻辑，提供统一的缓存接口
"""

import threading
from typing import TypeVar, Optional, Generic, Callable, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from loguru import logger

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    data: T
    timestamp: datetime
    hit_count: int = 0

    @property
    def age_seconds(self) -> float:
        """获取缓存年龄（秒）"""
        return (datetime.now() - self.timestamp).total_seconds()

    def is_expired(self, ttl_seconds: int) -> bool:
        """检查是否过期"""
        return self.age_seconds > ttl_seconds


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0

    @property
    def total_requests(self) -> int:
        """总请求数"""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    def reset(self) -> None:
        """重置统计"""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.evictions = 0


class TTLCache(Generic[T]):
    """
    带TTL（过期时间）的缓存

    特性：
    - 线程安全
    - 自动过期
    - 统计信息
    - 可选的懒加载
    """

    def __init__(
        self,
        ttl: int = 30,
        max_size: int = None,
        name: str = "TTLCache"
    ):
        """
        初始化缓存

        Args:
            ttl: 过期时间（秒）
            max_size: 最大缓存条目数，None表示无限制
            name: 缓存名称（用于日志）
        """
        self._ttl = ttl
        self._max_size = max_size
        self._name = name

        self._cache: Dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()
        self._stats = CacheStats()

        logger.debug(f"缓存初始化: {name}, TTL={ttl}s, max_size={max_size}")

    def get(self, key: str) -> Optional[T]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，未命中或过期返回None
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                logger.debug(f"[{self._name}] 缓存未命中: {key}")
                return None

            if entry.is_expired(self._ttl):
                # 过期，删除
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                logger.debug(f"[{self._name}] 缓存过期: {key}")
                return None

            entry.hit_count += 1
            self._stats.hits += 1
            logger.debug(f"[{self._name}] 缓存命中: {key}")
            return entry.data

    def set(self, key: str, value: T) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            # 检查大小限制
            if self._max_size and len(self._cache) >= self._max_size:
                # 删除最老的条目（简单的LRU策略）
                oldest_key = min(self._cache.items(), key=lambda x: x[1].timestamp)[0]
                del self._cache[oldest_key]
                self._stats.evictions += 1
                logger.debug(f"[{self._name}] 缓存淘汰: {oldest_key}")

            self._cache[key] = CacheEntry(
                data=value,
                timestamp=datetime.now()
            )
            self._stats.sets += 1
            logger.debug(f"[{self._name}] 缓存设置: {key}")

    def get_or_load(
        self,
        key: str,
        loader: Callable[[], T],
        force_refresh: bool = False
    ) -> T:
        """
        获取缓存值，如果未命中则加载

        Args:
            key: 缓存键
            loader: 数据加载函数
            force_refresh: 是否强制刷新

        Returns:
            缓存值或加载的值
        """
        if not force_refresh:
            cached = self.get(key)
            if cached is not None:
                return cached

        # 加载数据
        data = loader()
        self.set(key, data)
        return data

    def delete(self, key: str) -> bool:
        """
        删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"[{self._name}] 缓存删除: {key}")
                return True
            return False

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            size = len(self._cache)
            self._cache.clear()
            logger.info(f"[{self._name}] 缓存已清空，删除 {size} 个条目")

    def cleanup_expired(self) -> int:
        """
        清理过期的缓存条目

        Returns:
            清理的条目数
        """
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if v.is_expired(self._ttl)
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats.evictions += 1

            if expired_keys:
                logger.debug(f"[{self._name}] 清理过期缓存: {len(expired_keys)} 个条目")

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            return {
                'name': self._name,
                'ttl': self._ttl,
                'max_size': self._max_size,
                'current_size': len(self._cache),
                'hits': self._stats.hits,
                'misses': self._stats.misses,
                'sets': self._stats.sets,
                'evictions': self._stats.evictions,
                'hit_rate': self._stats.hit_rate,
                'total_requests': self._stats.total_requests
            }

    def reset_stats(self) -> None:
        """重置统计信息"""
        with self._lock:
            self._stats.reset()

    @property
    def ttl(self) -> int:
        """获取TTL"""
        return self._ttl

    @property
    def size(self) -> int:
        """获取当前缓存大小"""
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        return self.get(key) is not None

    def __len__(self) -> int:
        """获取缓存大小"""
        return self.size
