"""
历史数据源适配器

实现IQuoteFetcher接口，为回测提供历史行情数据。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, List, Optional
from datetime import datetime, time
from loguru import logger

from backend.domain.interfaces import IQuoteFetcher
from backend.backtest.data_loader import HistoricalDataLoader
from backend.backtest.clock import TimeGranularity


class HistoricalQuoteFetcher(IQuoteFetcher):
    """
    历史行情数据获取器

    实现IQuoteFetcher接口，提供历史时点的行情数据。
    用于回测时替代实时数据源。
    """

    def __init__(
        self,
        stock_codes: List[str],
        etf_codes: List[str],
        start_date: str,
        end_date: str,
        granularity: TimeGranularity = TimeGranularity.DAILY,
        data_loader: Optional[HistoricalDataLoader] = None
    ):
        """
        初始化历史行情获取器

        Args:
            stock_codes: 股票代码列表
            etf_codes: ETF代码列表
            start_date: 开始日期 "YYYYMMDD"
            end_date: 结束日期 "YYYYMMDD"
            granularity: 时间粒度
            data_loader: 数据加载器（可选）
        """
        self._stock_codes = stock_codes
        self._etf_codes = etf_codes
        self._start_date = start_date
        self._end_date = end_date
        self._granularity = granularity
        self._data_loader = data_loader or HistoricalDataLoader()

        # 存储历史数据
        self._stock_data: Dict[str, Dict[datetime, Dict]] = {}
        self._etf_data: Dict[str, Dict[datetime, Dict]] = {}

        # 当前模拟时间
        self._current_time: Optional[datetime] = None

        # 是否已加载数据
        self._loaded = False

    def load_data(self, progress_callback=None) -> None:
        """
        预加载所有历史数据

        Args:
            progress_callback: 进度回调函数，签名为 (loaded_count, total_count)
        """
        if self._loaded:
            return

        logger.info("开始加载历史行情数据...")
        logger.info(f"股票: {len(self._stock_codes)}只, ETF: {len(self._etf_codes)}只")

        total_count = len(self._stock_codes) + len(self._etf_codes)
        loaded_count = 0

        # 加载股票数据
        for code in self._stock_codes:
            try:
                data = self._data_loader.load_stock_kline(
                    code, self._start_date, self._end_date, self._granularity
                )
                self._stock_data[code] = data
                logger.debug(f"加载股票 {code} 数据: {len(data)}条记录")
            except Exception as e:
                logger.warning(f"加载股票 {code} 数据失败: {e}")

            loaded_count += 1
            if progress_callback:
                progress_callback(loaded_count, total_count)

        # 加载ETF数据
        for code in self._etf_codes:
            try:
                data = self._data_loader.load_etf_kline(
                    code, self._start_date, self._end_date, self._granularity
                )
                self._etf_data[code] = data
                logger.debug(f"加载ETF {code} 数据: {len(data)}条记录")
            except Exception as e:
                logger.warning(f"加载ETF {code} 数据失败: {e}")

            loaded_count += 1
            if progress_callback:
                progress_callback(loaded_count, total_count)

        total_records = sum(len(d) for d in self._stock_data.values()) + \
                        sum(len(d) for d in self._etf_data.values())
        logger.info(f"历史数据加载完成，共 {total_records} 条记录")
        self._loaded = True

    def set_current_time(self, current_time: datetime) -> None:
        """
        设置当前模拟时间点

        Args:
            current_time: 当前时间
        """
        self._current_time = current_time

    def get_stock_quote(self, stock_code: str) -> Optional[Dict]:
        """
        获取指定时间的股票行情

        Args:
            stock_code: 股票代码

        Returns:
            行情字典，未找到返回None
        """
        if self._current_time is None:
            logger.warning("未设置当前时间，无法获取行情")
            return None

        # 标准化代码
        normalized_code = self._normalize_code(stock_code)

        # 获取该股票的历史数据
        stock_history = self._stock_data.get(normalized_code)
        if not stock_history:
            logger.debug(f"未找到股票 {stock_code} 的历史数据")
            return None

        # 日级别：找到该日期的数据
        if self._granularity == TimeGranularity.DAILY:
            return self._find_daily_quote(stock_history, stock_code)

        # 分钟级别：找到最接近的数据
        return self._find_minute_quote(stock_history, stock_code)

    def get_batch_quotes(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取股票行情

        Args:
            stock_codes: 股票代码列表

        Returns:
            {股票代码: 行情数据}
        """
        result = {}
        for code in stock_codes:
            quote = self.get_stock_quote(code)
            if quote:
                result[code] = quote
        return result

    def is_trading_time(self) -> bool:
        """判断是否在交易时间内"""
        if self._current_time is None:
            return False

        current_time = self._current_time.time()

        # 交易时间：9:30-11:30, 13:00-15:00
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)

        return (
            morning_start <= current_time <= morning_end or
            afternoon_start <= current_time <= afternoon_end
        )

    def get_time_to_close(self) -> int:
        """
        获取距离收盘的秒数

        Returns:
            距离15:00收盘的秒数，不在交易时间返回-1
        """
        if self._current_time is None or not self.is_trading_time():
            return -1

        current_time = self._current_time.time()
        current_date = self._current_time.date()

        # 计算收盘时间
        if current_time <= time(11, 30):
            # 上午时段
            close_time = datetime.combine(current_date, time(11, 30))
        else:
            # 下午时段
            close_time = datetime.combine(current_date, time(15, 0))

        delta = close_time - self._current_time
        return int(delta.total_seconds())

    def get_etf_quote(self, etf_code: str) -> Optional[Dict]:
        """
        获取指定时间的ETF行情

        Args:
            etf_code: ETF代码

        Returns:
            行情字典，未找到返回None
        """
        if self._current_time is None:
            return None

        # 标准化代码
        normalized_code = self._normalize_code(etf_code)

        # 获取该ETF的历史数据
        etf_history = self._etf_data.get(normalized_code)
        if not etf_history:
            logger.debug(f"未找到ETF {etf_code} 的历史数据")
            return None

        # 日级别：找到该日期的数据
        if self._granularity == TimeGranularity.DAILY:
            return self._find_daily_quote(etf_history, etf_code, is_etf=True)

        # 分钟级别：找到最接近的数据
        return self._find_minute_quote(etf_history, etf_code, is_etf=True)

    def get_etf_batch_quotes(self, etf_codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取ETF行情

        Args:
            etf_codes: ETF代码列表

        Returns:
            {ETF代码: 行情数据}
        """
        result = {}
        for code in etf_codes:
            quote = self.get_etf_quote(code)
            if quote:
                result[code] = quote
        return result

    def check_liquidity(
        self,
        etf_code: str,
        min_amount: float
    ) -> bool:
        """
        检查ETF流动性

        Args:
            etf_code: ETF代码
            min_amount: 最小成交额（元）

        Returns:
            是否满足流动性要求
        """
        quote = self.get_etf_quote(etf_code)
        if not quote:
            return False

        # 日级别使用当天成交额
        amount = quote.get("amount", 0)
        return amount >= min_amount

    def _find_daily_quote(
        self,
        history: Dict[datetime, Dict],
        code: str,
        is_etf: bool = False
    ) -> Optional[Dict]:
        """查找日级别行情"""
        current_date = self._current_time.date()

        # 精确匹配日期
        if self._current_time in history:
            return self._copy_quote_with_code(history[self._current_time], code)

        # 尝试找到同一天的数据（时间可能不同）
        for dt, quote in history.items():
            if dt.date() == current_date:
                return self._copy_quote_with_code(quote, code)

        return None

    def _find_minute_quote(
        self,
        history: Dict[datetime, Dict],
        code: str,
        is_etf: bool = False
    ) -> Optional[Dict]:
        """查找分钟级别行情（找最接近的）"""
        # 找到时间差最小的数据
        best_dt, min_delta = self._find_closest_datetime(history.keys())

        # 如果时间差超过1小时，认为没有有效数据
        if best_dt and min_delta <= 3600:
            return self._copy_quote_with_code(history[best_dt], code)

        return None

    @staticmethod
    def _copy_quote_with_code(quote: Dict, code: str) -> Dict:
        """复制行情数据并添加代码"""
        result = quote.copy()
        result["code"] = code
        return result

    def _find_closest_datetime(
        self,
        datetimes: Dict[datetime, Dict].keys()
    ) -> tuple:
        """找到最接近当前时间的时间点"""
        best_dt = None
        min_delta = float('inf')

        for dt in datetimes:
            delta = abs((dt - self._current_time).total_seconds())
            if delta < min_delta:
                min_delta = delta
                best_dt = dt

        return best_dt, min_delta

    @staticmethod
    def _normalize_code(code: str) -> str:
        """标准化代码，去掉市场前缀"""
        prefixes = ['sh', 'sz', 'bj']
        code_lower = code.lower()
        for prefix in prefixes:
            if code_lower.startswith(prefix):
                return code[2:]
        return code

    def get_available_dates(self) -> List[datetime]:
        """获取有数据的日期列表"""
        all_dates = set()

        for stock_history in self._stock_data.values():
            all_dates.update(dt.date() for dt in stock_history.keys())

        for etf_history in self._etf_data.values():
            all_dates.update(dt.date() for dt in etf_history.keys())

        return sorted([datetime.combine(d, time(0, 0)) for d in all_dates])

    def get_data_summary(self) -> Dict:
        """获取数据摘要"""
        return {
            "stock_codes": list(self._stock_data.keys()),
            "etf_codes": list(self._etf_data.keys()),
            "stock_records": sum(len(d) for d in self._stock_data.values()),
            "etf_records": sum(len(d) for d in self._etf_data.values()),
            "granularity": self._granularity.value,
            "loaded": self._loaded
        }
