"""
A股实时行情数据获取模块
使用AKShare获取实时行情数据
优化：后台定时刷新 + 读取缓存
"""

import akshare as ak
import pandas as pd
import time
import atexit
from typing import Dict, List, Optional
from datetime import datetime, time as dt_time
from loguru import logger
import threading


class StockQuoteFetcher:
    """A股行情数据获取器 - 基于AKShare，后台定时刷新"""

    # 类变量，用于缓存行情数据
    _cache_lock = threading.Lock()
    _spot_cache = None
    _cache_time = None
    _cache_ttl = 30  # 缓存有效期30秒（业务读取容忍度）
    _refresh_interval = 15  # 后台刷新间隔15秒
    _refresh_thread = None
    _running = False
    _initialized = False

    def __init__(self):
        self.data_source = 'AKShare'
        # 启动时初始化，确保有数据
        self._ensure_initialized()

    def _ensure_initialized(self):
        """确保数据已初始化"""
        if not StockQuoteFetcher._initialized:
            logger.info("首次启动，正在初始化A股行情数据...")
            self._fetch_data()
            StockQuoteFetcher._initialized = True
            # 启动后台刷新线程
            self._start_background_refresh()
            # 注册退出处理
            atexit.register(self._stop_background_refresh)

    def _fetch_data(self) -> pd.DataFrame:
        """实际获取数据的方法"""
        try:
            logger.debug("正在从AKShare获取A股实时行情...")
            start_time = time.time()
            df = ak.stock_zh_a_spot_em()
            elapsed = time.time() - start_time
            logger.info(f"成功获取 {len(df)} 只A股的实时行情数据 (耗时: {elapsed:.1f}秒)")

            with self._cache_lock:
                self._spot_cache = df
                self._cache_time = time.time()

            return df

        except Exception as e:
            logger.error(f"获取A股行情失败: {e}")
            # 如果有旧缓存，返回旧缓存
            if self._spot_cache is not None:
                logger.warning("使用缓存的行情数据")
                return self._spot_cache
            return pd.DataFrame()

    def _background_refresh_worker(self):
        """后台刷新工作线程"""
        logger.info(f"后台刷新线程已启动，刷新间隔: {self._refresh_interval}秒")
        while self._running:
            try:
                time.sleep(self._refresh_interval)
                if self._running:
                    self._fetch_data()
            except Exception as e:
                logger.error(f"后台刷新异常: {e}")
        logger.info("后台刷新线程已停止")

    def _start_background_refresh(self):
        """启动后台刷新线程"""
        if self._refresh_thread is None or not self._refresh_thread.is_alive():
            self._running = True
            self._refresh_thread = threading.Thread(
                target=self._background_refresh_worker,
                daemon=True,
                name="StockQuoteRefresh"
            )
            self._refresh_thread.start()
            logger.info("后台刷新线程已启动")

    def _stop_background_refresh(self):
        """停止后台刷新线程"""
        if self._running:
            self._running = False
            if self._refresh_thread and self._refresh_thread.is_alive():
                self._refresh_thread.join(timeout=2)
            logger.info("后台刷新线程已停止")

    def _get_spot_data(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        获取沪深A股实时行情数据（从缓存读取）

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            包含所有A股行情的DataFrame
        """
        current_time = time.time()

        # 检查缓存
        if not force_refresh and self._spot_cache is not None:
            cache_age = current_time - self._cache_time
            if cache_age < self._cache_ttl:
                logger.debug(f"使用缓存数据 (缓存年龄: {cache_age:.1f}秒)")
                return self._spot_cache

        # 如果强制刷新或缓存过期，等待后台线程更新（最多等待5秒）
        if force_refresh or (self._spot_cache is not None and current_time - self._cache_time >= self._cache_ttl):
            logger.info("缓存已过期或强制刷新，触发后台更新...")
            # 触发后台更新
            with self._cache_lock:
                if self._spot_cache is not None:
                    cache_age = current_time - self._cache_time
                    if cache_age < self._cache_ttl:
                        return self._spot_cache

        # 返回当前缓存（即使可能稍旧）
        if self._spot_cache is not None:
            return self._spot_cache

        # 如果完全没有缓存，同步获取一次
        return self._fetch_data()

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
        try:
            # AKShare字段映射
            code = str(row.get('代码', ''))
            name = str(row.get('名称', ''))
            price = float(row.get('最新价', 0)) or 0
            prev_close = float(row.get('昨收', 0)) or 0
            open_price = float(row.get('今开', 0)) or 0
            high = float(row.get('最高', 0)) or 0
            low = float(row.get('最低', 0)) or 0
            volume = int(float(row.get('成交量', 0))) or 0  # AKShare返回的是手
            amount = float(row.get('成交额', 0)) or 0  # 元
            change_pct = float(row.get('涨跌幅', 0)) or 0

            # 如果当前价为0（未开盘或停牌），使用昨收价代替
            if price == 0 and prev_close > 0:
                price = prev_close
                change = 0
                change_pct = 0
            else:
                change = price - prev_close

            # 判断是否涨停
            is_limit_up = self._is_limit_up(code, change_pct)
            is_limit_down = self._is_limit_down(code, change_pct)

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
                'is_limit_up': is_limit_up,
                'is_limit_down': is_limit_down,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'data_source': 'AKShare'
            }

        except (ValueError, TypeError) as e:
            logger.error(f"解析股票数据失败: {e}")
            return None

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

            results = {}
            for _, row in filtered_df.iterrows():
                code = str(row['代码'])
                quote = self._parse_stock_row(row)
                if quote:
                    results[code] = quote

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

            results = {}
            for _, row in df.iterrows():
                code = str(row['代码'])
                quote = self._parse_stock_row(row)
                if quote:
                    results[code] = quote

            return results

        except Exception as e:
            logger.error(f"获取所有股票行情失败: {e}")
            return {}

    def _is_limit_up(self, code: str, change_pct: float) -> bool:
        """判断是否涨停"""
        if change_pct < 0.095:
            return False

        if code.startswith('688') or code.startswith('300'):
            return change_pct >= 0.195
        elif code.startswith('8') or code.startswith('4'):
            return change_pct >= 0.295
        else:
            return change_pct >= 0.095

    def _is_limit_down(self, code: str, change_pct: float) -> bool:
        """判断是否跌停"""
        if change_pct > -0.095:
            return False

        if code.startswith('688') or code.startswith('300'):
            return change_pct <= -0.195
        elif code.startswith('8') or code.startswith('4'):
            return change_pct <= -0.295
        else:
            return change_pct <= -0.095

    def is_trading_time(self) -> bool:
        """判断是否在交易时间内"""
        now = datetime.now().time()

        # 上午: 9:30-11:30
        morning_start = dt_time(9, 30)
        morning_end = dt_time(11, 30)

        # 下午: 13:00-15:00
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

    def get_cache_status(self) -> Dict:
        """获取缓存状态"""
        with self._cache_lock:
            return {
                'initialized': self._initialized,
                'cache_exists': self._spot_cache is not None,
                'cache_age': time.time() - self._cache_time if self._cache_time else None,
                'cache_size': len(self._spot_cache) if self._spot_cache is not None else 0,
                'refresh_thread_alive': self._refresh_thread.is_alive() if self._refresh_thread else False
            }

    def clear_cache(self):
        """清除缓存"""
        with self._cache_lock:
            self._spot_cache = None
            self._cache_time = None
            logger.debug("行情数据缓存已清除")


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

    # 等待观察后台刷新
    print("\n等待后台刷新...")
    time.sleep(20)

    status = fetcher.get_cache_status()
    print(f"刷新后缓存状态: {status}")
