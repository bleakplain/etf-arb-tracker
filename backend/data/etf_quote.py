"""
ETF行情数据获取模块
使用AKShare获取ETF实时行情数据
优化：后台定时刷新 + 读取缓存
"""

import akshare as ak
import pandas as pd
import time
import atexit
from typing import Dict, List
from datetime import datetime
from loguru import logger
import threading


class ETFQuoteFetcher:
    """ETF行情获取器 - 基于AKShare，后台定时刷新"""

    # 类变量，用于缓存ETF行情数据
    _cache_lock = threading.Lock()
    _etf_cache = None
    _cache_time = None
    _cache_ttl = 30  # 缓存有效期30秒
    _refresh_interval = 15  # 后台刷新间隔15秒
    _refresh_thread = None
    _running = False
    _initialized = False

    def __init__(self):
        self.data_source = 'AKShare'
        self.etf_limits = {
            'default': 0.10,
            'bond': 0.10,
            'gold': 0.10,
            'cross': 0.10,
            'commodity': 0.10
        }
        # 启动时初始化
        self._ensure_initialized()

    def _ensure_initialized(self):
        """确保数据已初始化"""
        if not ETFQuoteFetcher._initialized:
            logger.info("首次启动，正在初始化ETF行情数据...")
            self._fetch_data()
            ETFQuoteFetcher._initialized = True
            # 启动后台刷新线程
            self._start_background_refresh()
            # 注册退出处理
            atexit.register(self._stop_background_refresh)

    def _fetch_data(self) -> pd.DataFrame:
        """实际获取数据的方法"""
        try:
            logger.debug("正在从AKShare获取ETF实时行情...")
            start_time = time.time()
            df = ak.fund_etf_spot_em()
            elapsed = time.time() - start_time
            logger.info(f"成功获取 {len(df)} 只ETF的实时行情数据 (耗时: {elapsed:.1f}秒)")

            with self._cache_lock:
                self._etf_cache = df
                self._cache_time = time.time()

            return df

        except Exception as e:
            logger.error(f"获取ETF行情失败: {e}")
            if self._etf_cache is not None:
                logger.warning("使用缓存的ETF行情数据")
                return self._etf_cache
            return pd.DataFrame()

    def _background_refresh_worker(self):
        """后台刷新工作线程"""
        logger.info(f"ETF后台刷新线程已启动，刷新间隔: {self._refresh_interval}秒")
        while self._running:
            try:
                time.sleep(self._refresh_interval)
                if self._running:
                    self._fetch_data()
            except Exception as e:
                logger.error(f"ETF后台刷新异常: {e}")
        logger.info("ETF后台刷新线程已停止")

    def _start_background_refresh(self):
        """启动后台刷新线程"""
        if self._refresh_thread is None or not self._refresh_thread.is_alive():
            self._running = True
            self._refresh_thread = threading.Thread(
                target=self._background_refresh_worker,
                daemon=True,
                name="ETFQuoteRefresh"
            )
            self._refresh_thread.start()
            logger.info("ETF后台刷新线程已启动")

    def _stop_background_refresh(self):
        """停止后台刷新线程"""
        if self._running:
            self._running = False
            if self._refresh_thread and self._refresh_thread.is_alive():
                self._refresh_thread.join(timeout=2)
            logger.info("ETF后台刷新线程已停止")

    def _get_etf_spot_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        获取所有ETF实时行情数据（从缓存读取）

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            包含所有ETF行情的DataFrame
        """
        current_time = time.time()

        # 检查缓存
        if not force_refresh and self._etf_cache is not None:
            cache_age = current_time - self._cache_time
            if cache_age < self._cache_ttl:
                logger.debug(f"使用ETF缓存数据 (缓存年龄: {cache_age:.1f}秒)")
                return self._etf_cache

        # 如果完全没有缓存，同步获取一次
        if self._etf_cache is None:
            return self._fetch_data()

        # 返回当前缓存
        return self._etf_cache

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
            return self._parse_etf_row(row)

        except Exception as e:
            logger.error(f"获取ETF {etf_code} 行情失败: {e}")
            return None

    def _parse_etf_row(self, row: pd.Series) -> Dict:
        """解析单行ETF数据"""
        try:
            code = str(row.get('代码', ''))
            name = str(row.get('名称', ''))
            price = float(row.get('最新价', 0)) or 0
            prev_close = float(row.get('昨收', 0)) or 0
            open_price = float(row.get('今开', 0)) or 0
            high = float(row.get('最高', 0)) or 0
            low = float(row.get('最低', 0)) or 0
            volume = int(float(row.get('成交量', 0))) or 0  # 手
            amount = float(row.get('成交额', 0)) or 0  # 元
            change_pct = float(row.get('涨跌幅', 0)) or 0

            if price == 0 and prev_close > 0:
                price = prev_close
                change = 0
                change_pct = 0
            else:
                change = price - prev_close

            return {
                'code': code,
                'name': name,
                'price': price,
                'prev_close': prev_close,
                'open': open_price,
                'high': high,
                'low': low,
                'volume': volume,
                'amount': amount,
                'change': change,
                'change_pct': change_pct,
                'asset_type': 'ETF',
                'iopv': self._get_iopv(code),
                'premium': None,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'data_source': 'AKShare'
            }

        except (ValueError, TypeError) as e:
            logger.error(f"解析ETF数据失败: {e}")
            return None

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

            results = {}
            for _, row in filtered_df.iterrows():
                code = str(row['代码'])
                quote = self._parse_etf_row(row)
                if quote:
                    results[code] = quote

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

            results = {}
            for _, row in df.iterrows():
                code = str(row['代码'])
                quote = self._parse_etf_row(row)
                if quote:
                    results[code] = quote

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

    def get_cache_status(self) -> Dict:
        """获取缓存状态"""
        with self._cache_lock:
            return {
                'initialized': self._initialized,
                'cache_exists': self._etf_cache is not None,
                'cache_age': time.time() - self._cache_time if self._cache_time else None,
                'cache_size': len(self._etf_cache) if self._etf_cache is not None else 0,
                'refresh_thread_alive': self._refresh_thread.is_alive() if self._refresh_thread else False
            }

    def clear_cache(self):
        """清除缓存"""
        with self._cache_lock:
            self._etf_cache = None
            self._cache_time = None
            logger.debug("ETF行情数据缓存已清除")


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
