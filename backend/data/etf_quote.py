"""
ETF行情数据获取模块
使用新的数据管理器架构
优化：后台定时刷新 + 读取缓存
"""

import pandas as pd
from typing import Dict, List
from datetime import datetime
from loguru import logger

from backend.data.cache_base import BaseCachedFetcher
from backend.data.parsers import parse_quote_row, batch_parse_quotes


class ETFQuoteFetcher(BaseCachedFetcher):
    """ETF行情获取器 - 使用新数据管理器架构"""

    # 类变量
    _cache_lock = None
    _etf_cache = None
    _cache_time = None
    _cache_ttl = 30  # 默认缓存有效期30秒，可通过配置覆盖
    _refresh_interval = 15  # 默认刷新间隔15秒，可通过配置覆盖
    _refresh_thread = None
    _running = False
    _initialized = False
    _data_manager = None

    def __init__(self, config: dict = None):
        self.data_source = 'DataManager'
        self._config = config or {}
        self.etf_limits = {
            'default': 0.10,
            'bond': 0.10,
            'gold': 0.10,
            'cross': 0.10,
            'commodity': 0.10
        }
        super().__init__(config)

        # 从配置读取刷新参数
        if config:
            refresh_config = config.get('refresh', {})
            self._refresh_interval = refresh_config.get('backend_cache_interval', 15)
            self._cache_ttl = refresh_config.get('backend_cache_ttl', 30)

    def _fetch_data(self) -> pd.DataFrame:
        """实际获取数据的方法 - 使用数据管理器"""
        try:
            if self._data_manager is None:
                from backend.data.data_manager import get_data_manager
                self._data_manager = get_data_manager(self._config)

            logger.debug("正在从数据管理器获取ETF实时行情...")
            import time
            start_time = time.time()
            df = self._data_manager.fetch_etf_spot()
            elapsed = time.time() - start_time

            if df.empty:
                raise ValueError("获取数据为空")

            logger.info(f"成功获取 {len(df)} 只ETF的实时行情数据 (耗时: {elapsed:.2f}秒)")

            self._etf_cache = df
            self._cache_time = time.time()

            return df

        except Exception as e:
            logger.error(f"获取ETF行情失败: {e}")
            if self._etf_cache is not None:
                logger.warning("使用缓存的ETF行情数据")
                return self._etf_cache
            return pd.DataFrame()

    def _get_etf_spot_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        获取所有ETF实时行情数据（从缓存读取）

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            包含所有ETF行情的DataFrame
        """
        return self._get_cached_data(force_refresh)

    def get_etf_quote(self, etf_code: str) -> Dict:
        """
        获取ETF实时行情（从缓存读取，快速响应）

        Args:
            etf_code: ETF代码

        Returns:
            ETF行情数据字典
        """
        try:
            df = self._get_etf_spot_data()

            if df.empty:
                logger.error("无法获取ETF行情数据")
                return None

            # 查找指定ETF
            etf_row = df[df['代码'] == etf_code]

            if etf_row.empty:
                logger.warning(f"未找到ETF {etf_code}")
                return None

            row = etf_row.iloc[0]
            quote = parse_quote_row(row, asset_type='etf')
            if quote:
                quote['data_source'] = self._get_current_source()
                quote['iopv'] = self._get_iopv(code)
            return quote

        except Exception as e:
            logger.error(f"获取ETF {etf_code} 行情失败: {e}")
            return None

    def _parse_etf_row(self, row: pd.Series) -> Dict:
        """解析单行ETF数据"""
        quote = parse_quote_row(row, asset_type='etf')
        if quote:
            quote['data_source'] = self._get_current_source()
            quote['iopv'] = self._get_iopv(quote['code'])
        return quote

    def _get_iopv(self, etf_code: str) -> float:
        """获取ETF的IOPV（暂时返回0）"""
        return 0.0

    def get_etf_batch_quotes(self, etf_codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取ETF行情（从缓存读取，快速响应）

        Args:
            etf_codes: ETF代码列表

        Returns:
            {ETF代码: 行情数据}
        """
        try:
            df = self._get_etf_spot_data()

            if df.empty:
                return {}

            # 筛选指定的ETF
            filtered_df = df[df['代码'].isin(etf_codes)]

            results = batch_parse_quotes(filtered_df, asset_type='etf')
            for quote in results.values():
                quote['data_source'] = self._get_current_source()
                quote['iopv'] = self._get_iopv(quote['code'])

            logger.info(f"批量获取 {len(results)}/{len(etf_codes)} 只ETF行情")
            return results

        except Exception as e:
            logger.error(f"批量获取ETF行情失败: {e}")
            return {}

    def get_all_etfs(self) -> Dict[str, Dict]:
        """
        获取所有ETF的行情数据（从缓存读取，快速响应）

        Returns:
            {ETF代码: 行情数据}
        """
        try:
            df = self._get_etf_spot_data()

            if df.empty:
                return {}

            results = batch_parse_quotes(df, asset_type='etf')
            for quote in results.values():
                quote['data_source'] = self._get_current_source()
                quote['iopv'] = self._get_iopv(quote['code'])

            return results

        except Exception as e:
            logger.error(f"获取所有ETF行情失败: {e}")
            return {}

    def check_liquidity(self, etf_code: str, min_amount: float = 50000000) -> bool:
        """检查ETF流动性"""
        quote = self.get_etf_quote(etf_code)

        if not quote:
            return False

        current_amount = quote.get('amount', 0)
        return current_amount >= min_amount / 4

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
        self._etf_cache = None
        self._cache_time = None


# 测试代码
if __name__ == "__main__":
    fetcher = ETFQuoteFetcher()

    # 显示缓存状态
    status = fetcher.get_cache_status()
    print(f"缓存状态: {status}")

    # 测试获取ETF行情
    etf_codes = ["510300", "510500", "159915", "588000"]

    print("\n=== ETF行情测试（从缓存读取） ===")
    import time

    start = time.time()
    quotes = fetcher.get_etf_batch_quotes(etf_codes)
    elapsed = time.time() - start

    print(f"批量获取 {len(quotes)} 只ETF，响应时间: {elapsed*1000:.1f}毫秒")

    for code, quote in quotes.items():
        print(f"{quote['name']} ({code}):")
        print(f"  价格: {quote['price']:.3f}")
        print(f"  涨跌幅: {quote['change_pct']:+.2f}%")

    # 等待观察后台刷新
    print("\n等待后台刷新...")
    time.sleep(20)

    status = fetcher.get_cache_status()
    print(f"刷新后缓存状态: {status}")
