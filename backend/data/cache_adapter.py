"""
缓存适配器 - 使用新的TTL缓存组件

将现有的缓存逻辑迁移到统一的TTLCache组件
"""

import time
import atexit
import threading
from typing import Optional, Dict, Any, Callable
from loguru import logger
import pandas as pd

from backend.infrastructure.cache import TTLCache


class CachedDataFetcher:
    """
    使用TTLCache的数据获取器

    替代原有的类变量缓存方式，提供更清晰的缓存管理
    """

    def __init__(
        self,
        fetcher_func: Callable[[], pd.DataFrame],
        ttl: int = 30,
        refresh_interval: int = 15,
        name: str = "CachedDataFetcher"
    ):
        """
        初始化缓存数据获取器

        Args:
            fetcher_func: 数据获取函数
            ttl: 缓存过期时间（秒）
            refresh_interval: 后台刷新间隔（秒）
            name: 缓存名称
        """
        self._fetcher_func = fetcher_func
        self._cache = TTLCache(ttl=ttl, name=name)
        self._refresh_interval = refresh_interval
        self._name = name

        # 后台刷新
        self._running = False
        self._refresh_thread: Optional[threading.Thread] = None

        # 首次初始化
        self._ensure_initialized()

    def _ensure_initialized(self):
        """确保数据已初始化"""
        logger.info(f"{self._name} 首次启动，正在初始化...")
        self._load_data()
        self._start_background_refresh()
        atexit.register(self._stop_background_refresh)

    def _load_data(self) -> pd.DataFrame:
        """加载数据"""
        data = self._fetcher_func()
        self._cache.set("data", data)
        return data

    def _background_refresh_worker(self):
        """后台刷新工作线程"""
        logger.info(f"{self._name} 后台刷新线程已启动，刷新间隔: {self._refresh_interval}秒")

        while self._running:
            try:
                time.sleep(self._refresh_interval)
                if self._running:
                    self._load_data()
            except Exception as e:
                logger.error(f"{self._name} 后台刷新异常: {e}")

        logger.info(f"{self._name} 后台刷新线程已停止")

    def _start_background_refresh(self):
        """启动后台刷新线程"""
        if self._refresh_thread is None or not self._refresh_thread.is_alive():
            self._running = True
            self._refresh_thread = threading.Thread(
                target=self._background_refresh_worker,
                daemon=True,
                name=f"{self._name}Refresh"
            )
            self._refresh_thread.start()
            logger.info(f"{self._name} 后台刷新线程已启动")

    def _stop_background_refresh(self):
        """停止后台刷新线程"""
        if self._running:
            self._running = False
            if self._refresh_thread and self._refresh_thread.is_alive():
                self._refresh_thread.join(timeout=2)
            logger.info(f"{self._name} 后台刷新线程已停止")

    def get_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        获取缓存数据

        Args:
            force_refresh: 是否强制刷新

        Returns:
            DataFrame
        """
        if force_refresh:
            return self._load_data()

        data = self._cache.get("data")
        if data is None:
            return self._load_data()

        return data

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self._cache.get_stats()

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()


def create_cached_fetcher(
    fetcher_func: Callable[[], pd.DataFrame],
    ttl: int = 30,
    refresh_interval: int = 15,
    name: str = "CachedFetcher"
) -> CachedDataFetcher:
    """
    创建缓存数据获取器

    Args:
        fetcher_func: 数据获取函数
        ttl: 缓存过期时间（秒）
        refresh_interval: 后台刷新间隔（秒）
        name: 缓存名称

    Returns:
        CachedDataFetcher实例
    """
    return CachedDataFetcher(
        fetcher_func=fetcher_func,
        ttl=ttl,
        refresh_interval=refresh_interval,
        name=name
    )
