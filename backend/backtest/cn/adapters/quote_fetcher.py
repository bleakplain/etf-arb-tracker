"""
回测行情数据适配器

将历史数据加载器适配为 IQuoteFetcher 接口，
使 ArbitrageEngineCN 可以在回测环境中使用历史数据。
"""

from typing import Dict, List, Optional
from loguru import logger

from backend.market.interfaces import IQuoteFetcher
from backend.backtest.data_loader import HistoricalDataLoader
from backend.backtest.clock import TimeGranularity


class HistoricalQuoteFetcherAdapter(IQuoteFetcher):
    """
    历史行情数据适配器

    将 HistoricalDataLoader 适配为 IQuoteFetcher 接口，
    用于回测场景。
    """

    def __init__(
        self,
        data_loader: HistoricalDataLoader,
        stock_codes: List[str],
        etf_codes: List[str],
        start_date: str,
        end_date: str,
        granularity: TimeGranularity = TimeGranularity.DAILY
    ):
        """
        初始化适配器

        Args:
            data_loader: 历史数据加载器
            stock_codes: 股票代码列表
            etf_codes: ETF代码列表
            start_date: 开始日期
            end_date: 结束日期
            granularity: 时间粒度
        """
        self._loader = data_loader
        self._stock_codes = stock_codes
        self._etf_codes = etf_codes
        self._start_date = start_date
        self._end_date = end_date
        self._granularity = granularity

        # 当前时间（回测模拟时间）
        self._current_time = None

        # 缓存加载的历史数据
        self._stock_data: Dict[str, Dict] = {}
        self._etf_data: Dict[str, Dict] = {}

    def load_data(self) -> None:
        """加载历史数据"""
        logger.info("开始加载历史数据...")

        # 并行加载股票数据
        stock_data = self._loader.load_batch_kline(
            self._stock_codes,
            self._start_date,
            self._end_date,
            self._granularity,
            is_etf=False
        )
        self._stock_data = stock_data

        # 并行加载ETF数据
        etf_data = self._loader.load_batch_kline(
            self._etf_codes,
            self._start_date,
            self._end_date,
            self._granularity,
            is_etf=True
        )
        self._etf_data = etf_data

        logger.info(f"历史数据加载完成: {len(self._stock_data)}只股票, {len(self._etf_data)}个ETF")

    def set_current_time(self, current_time) -> None:
        """设置当前模拟时间"""
        self._current_time = current_time

    def get_stock_quote(self, code: str) -> Optional[Dict]:
        """获取单个股票行情（当前时间点）"""
        if not self._current_time:
            raise RuntimeError("未设置当前时间，请先调用 set_current_time()")

        data = self._stock_data.get(code)
        if not data:
            return None

        # 获取当前时间点最接近的行情
        return self._get_quote_at_time(data, self._current_time)

    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取股票行情（当前时间点）"""
        results = {}
        for code in codes:
            results[code] = self.get_stock_quote(code)
        return results

    def is_trading_time(self) -> bool:
        """判断是否交易时间"""
        if not self._current_time:
            return False
        # 简化：回测总是返回 True，由时钟控制
        return True

    def get_etf_quote(self, etf_code: str) -> Optional[Dict]:
        """获取ETF行情（当前时间点）"""
        if not self._current_time:
            raise RuntimeError("未设置当前时间，请先调用 set_current_time()")

        data = self._etf_data.get(etf_code)
        if not data:
            return None

        return self._get_quote_at_time(data, self._current_time)

    def get_etf_batch_quotes(self, etf_codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取ETF行情"""
        results = {}
        for code in etf_codes:
            results[code] = self.get_etf_quote(code)
        return results

    def check_liquidity(self, etf_code: str, min_amount: float) -> bool:
        """检查ETF流动性"""
        quote = self.get_etf_quote(etf_code)
        if not quote:
            return False
        return quote.get('amount', 0) >= min_amount

    def _get_quote_at_time(self, data: Dict, target_time) -> Optional[Dict]:
        """获取指定时间点的行情"""
        from datetime import datetime

        target_date = target_time.date() if isinstance(target_time, datetime) else target_time

        # 如果是日级别粒度，直接获取当天的数据
        if self._granularity == TimeGranularity.DAILY:
            for dt, quote in data.items():
                data_date = dt.date() if isinstance(dt, datetime) else dt
                if data_date == target_date:
                    return quote
            return None

        # 分钟级别：找到同一天内最接近的时间点
        best_match = None
        min_diff = float('inf')

        for dt, quote in data.items():
            # 确保只匹配同一天的数据
            data_date = dt.date() if isinstance(dt, datetime) else dt
            if data_date != target_date:
                continue

            diff = abs((dt - target_time).total_seconds())
            if diff < min_diff:
                min_diff = diff
                best_match = quote

        return best_match if min_diff < 3600 else None  # 1小时内有效
