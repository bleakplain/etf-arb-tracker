"""
A股实时行情数据获取模块
使用新的数据管理器架构（腾讯免费数据源）
优化：后台定时刷新 + 读取缓存
"""

import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, time as dt_time
from loguru import logger

from backend.data.cache_base import BaseCachedFetcher
from backend.data.parsers import parse_quote_row, batch_parse_quotes


class StockQuoteFetcher(BaseCachedFetcher):
    """A股行情数据获取器 - 使用新数据管理器架构"""

    # 类变量
    _cache_lock = None
    _spot_cache = None
    _cache_time = None
    _cache_ttl = 30
    _refresh_interval = 15
    _refresh_thread = None
    _running = False
    _initialized = False
    _data_manager = None

    def __init__(self, config: Optional[Dict] = None):
        self.data_source = 'DataManager'
        super().__init__(config)

    def _fetch_data(self) -> pd.DataFrame:
        """实际获取数据的方法 - 使用数据管理器"""
        try:
            if self._data_manager is None:
                from backend.data.data_manager import get_data_manager
                self._data_manager = get_data_manager(self._config)

            logger.debug("正在从数据管理器获取A股实时行情...")
            import time
            start_time = time.time()
            df = self._data_manager.fetch_stock_spot()
            elapsed = time.time() - start_time

            if df.empty:
                # 检查是否有可用缓存
                if self._spot_cache is not None:
                    cache_age = time.time() - self._cache_time
                    if cache_age < 300:
                        logger.warning(f"数据源暂时不可用，使用缓存数据 (缓存年龄: {cache_age:.1f}秒)")
                        return self._spot_cache
                raise ValueError("获取数据为空且无可用缓存")

            logger.info(f"成功获取 {len(df)} 只A股的实时行情数据 (耗时: {elapsed:.2f}秒)")

            self._spot_cache = df
            self._cache_time = time.time()

            return df

        except Exception as e:
            logger.error(f"获取A股行情失败: {e}")
            if self._spot_cache is not None:
                cache_age = time.time() - self._cache_time
                logger.warning(f"使用缓存的行情数据 (缓存年龄: {cache_age:.1f}秒)")
                return self._spot_cache
            return pd.DataFrame()

    def _get_spot_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        获取沪深A股实时行情数据（从缓存读取）

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            包含所有A股行情的DataFrame
        """
        return self._get_cached_data(force_refresh)

    def get_stock_quote(self, stock_code: str) -> Optional[Dict]:
        """
        获取单只股票的实时行情（从缓存读取，快速响应）

        Args:
            stock_code: 股票代码（6位数字）

        Returns:
            股票行情字典
        """
        try:
            df = self._get_spot_data()

            if df.empty:
                logger.error("无法获取行情数据")
                return None

            # 查找指定股票
            stock_row = df[df['代码'] == stock_code]

            if stock_row.empty:
                logger.warning(f"未找到股票 {stock_code}")
                return None

            row = stock_row.iloc[0]
            return self._parse_stock_row(row)

        except Exception as e:
            logger.error(f"获取股票 {stock_code} 行情失败: {e}")
            return None

    def _parse_stock_row(self, row: pd.Series) -> Dict:
        """解析单行股票数据"""
        quote = parse_quote_row(row, asset_type='stock')
        if quote:
            quote['data_source'] = self._get_current_source()
        return quote

    def get_batch_quotes(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取多只股票行情（从缓存读取，快速响应）

        Args:
            stock_codes: 股票代码列表

        Returns:
            {股票代码: 行情数据}
        """
        try:
            df = self._get_spot_data()

            if df.empty:
                return {}

            # 筛选指定的股票
            filtered_df = df[df['代码'].isin(stock_codes)]

            results = batch_parse_quotes(filtered_df, asset_type='stock')
            for quote in results.values():
                quote['data_source'] = self._get_current_source()

            logger.info(f"批量获取 {len(results)}/{len(stock_codes)} 只股票行情")
            return results

        except Exception as e:
            logger.error(f"批量获取股票行情失败: {e}")
            return {}

    def get_all_stocks(self) -> Dict[str, Dict]:
        """
        获取所有A股的行情数据（从缓存读取，快速响应）

        Returns:
            {股票代码: 行情数据}
        """
        try:
            df = self._get_spot_data()

            if df.empty:
                return {}

            results = batch_parse_quotes(df, asset_type='stock')
            for quote in results.values():
                quote['data_source'] = self._get_current_source()

            return results

        except Exception as e:
            logger.error(f"获取所有股票行情失败: {e}")
            return {}

    def is_trading_time(self) -> bool:
        """判断是否在交易时间内"""
        now = datetime.now().time()

        morning_start = dt_time(9, 30)
        morning_end = dt_time(11, 30)
        afternoon_start = dt_time(13, 0)
        afternoon_end = dt_time(15, 0)

        return (morning_start <= now <= morning_end or
                afternoon_start <= now <= afternoon_end)

    def get_time_to_close(self) -> int:
        """
        获取距离收盘的秒数

        Returns:
            距离15:00收盘的秒数，如果不在交易时间返回-1
        """
        now = datetime.now()
        close_time = now.replace(hour=15, minute=0, second=0, microsecond=0)

        if now.hour < 9 or now.hour >= 15:
            return -1

        delta = close_time - now
        return int(delta.total_seconds())

    @property
    def _cache_lock(self):
        """获取缓存锁"""
        import threading
        if not hasattr(self, '__cache_lock'):
            self.__cache_lock = threading.Lock()
        return self.__cache_lock

    def get_cache_status(self) -> Dict:
        """获取缓存状态"""
        return super().get_cache_status()

    def clear_cache(self):
        """清除缓存"""
        super().clear_cache()
        self._spot_cache = None
        self._cache_time = None


# 测试代码
if __name__ == "__main__":
    fetcher = StockQuoteFetcher()

    # 显示缓存状态
    status = fetcher.get_cache_status()
    print(f"缓存状态: {status}")

    # 测试获取单只股票（应该很快，因为读缓存）
    print("\n=== 测试获取股票行情（从缓存读取） ===")
    import time

    start = time.time()
    quote = fetcher.get_stock_quote("600519")
    elapsed = time.time() - start

    if quote:
        print(f"股票: {quote['name']} ({quote['code']})")
        print(f"价格: {quote['price']}")
        print(f"涨跌幅: {quote['change_pct']:.2f}%")
        print(f"响应时间: {elapsed*1000:.1f}毫秒")

    # 测试批量获取
    print("\n=== 测试批量获取 ===")
    codes = ["600519", "300750", "002594"]
    start = time.time()
    quotes = fetcher.get_batch_quotes(codes)
    elapsed = time.time() - start
    print(f"批量获取 {len(quotes)} 只股票，响应时间: {elapsed*1000:.1f}毫秒")
    for code, quote in quotes.items():
        print(f"{quote['name']}: {quote['price']:.2f} ({quote['change_pct']:+.2f}%)")
