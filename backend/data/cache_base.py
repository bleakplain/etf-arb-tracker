"""
缓存管理基类
提供后台刷新和缓存管理的通用功能
"""

import time
import atexit
import threading
from typing import Optional, Dict, Any
from loguru import logger
import pandas as pd


class BaseCachedFetcher:
    """
    带缓存的数据获取器基类

    提供：
    - 后台定时刷新
    - 缓存管理
    - 线程安全
    """

    # 类变量，由子类继承
    _cache_lock = threading.Lock()
    _cache = None
    _cache_time = None
    _cache_ttl = 30
    _refresh_interval = 15
    _refresh_thread = None
    _running = False
    _initialized = False
    _data_manager = None

    def __init__(self, config: Optional[Dict] = None):
        self._config = config or {}
        self._ensure_initialized()

    def _ensure_initialized(self):
        """确保数据已初始化"""
        if not self._initialized:
            logger.info(f"{self.__class__.__name__} 首次启动，正在初始化...")
            self._data_manager = self._get_data_manager()
            self._fetch_data()
            self._initialized = True
            self._start_background_refresh()
            atexit.register(self._stop_background_refresh)

    def _get_data_manager(self):
        """获取数据管理器，子类应覆盖此方法"""
        from backend.data.data_manager import get_data_manager
        return get_data_manager(self._config)

    def _fetch_data(self) -> pd.DataFrame:
        """
        实际获取数据的方法，子类必须实现

        Returns:
            DataFrame
        """
        raise NotImplementedError("子类必须实现 _fetch_data 方法")

    def _background_refresh_worker(self):
        """后台刷新工作线程"""
        logger.info(f"{self.__class__.__name__} 后台刷新线程已启动，刷新间隔: {self._refresh_interval}秒")
        while self._running:
            try:
                time.sleep(self._refresh_interval)
                if self._running:
                    self._fetch_data()
            except Exception as e:
                logger.error(f"{self.__class__.__name__} 后台刷新异常: {e}")
        logger.info(f"{self.__class__.__name__} 后台刷新线程已停止")

    def _start_background_refresh(self):
        """启动后台刷新线程"""
        if self._refresh_thread is None or not self._refresh_thread.is_alive():
            self._running = True
            self._refresh_thread = threading.Thread(
                target=self._background_refresh_worker,
                daemon=True,
                name=f"{self.__class__.__name__}Refresh"
            )
            self._refresh_thread.start()
            logger.info(f"{self.__class__.__name__} 后台刷新线程已启动")

    def _stop_background_refresh(self):
        """停止后台刷新线程"""
        if self._running:
            self._running = False
            if self._refresh_thread and self._refresh_thread.is_alive():
                self._refresh_thread.join(timeout=2)
            logger.info(f"{self.__class__.__name__} 后台刷新线程已停止")

    def _get_cached_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        获取缓存数据

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            DataFrame
        """
        current_time = time.time()

        # 检查缓存
        if not force_refresh and self._cache is not None:
            cache_age = current_time - self._cache_time
            if cache_age < self._cache_ttl:
                logger.debug(f"使用缓存数据 (缓存年龄: {cache_age:.1f}秒)")
                return self._cache

        # 如果完全没有缓存，同步获取一次
        if self._cache is None:
            return self._fetch_data()

        # 返回当前缓存
        return self._cache

    def get_cache_status(self) -> Dict[str, Any]:
        """获取缓存状态"""
        with self._cache_lock:
            return {
                'initialized': self._initialized,
                'cache_exists': self._cache is not None,
                'cache_age': time.time() - self._cache_time if self._cache_time else None,
                'cache_size': len(self._cache) if self._cache is not None else 0,
                'refresh_thread_alive': self._refresh_thread.is_alive() if self._refresh_thread else False
            }

    def clear_cache(self):
        """清除缓存"""
        with self._cache_lock:
            self._cache = None
            self._cache_time = None
            logger.debug(f"{self.__class__.__name__} 缓存已清除")

    def _get_current_source(self) -> str:
        """获取当前使用的数据源"""
        if self._data_manager:
            return 'DataManager'
        return 'Unknown'

    def get_data_source_metrics(self) -> Dict:
        """获取数据源性能指标"""
        if self._data_manager:
            return self._data_manager.get_metrics()
        return {}
