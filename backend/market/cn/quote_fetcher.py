"""
A股行情数据获取
"""

from typing import List, Dict, Optional
from datetime import time

from backend.market.interfaces import IQuoteFetcher
from backend.utils.clock import Clock, SystemClock, CHINA_TZ
from backend.utils.time_utils import is_trading_time


class CNStockQuoteProvider(IQuoteFetcher):
    """A股股票行情数据提供者"""

    def __init__(self, clock: Optional[Clock] = None):
        self._tencent_source = None
        self._clock = clock or SystemClock()

    def get_stock_quote(self, code: str) -> Optional[Dict]:
        """获取单个股票行情"""
        source = self._get_tencent_source()
        return source.get_quote(code)

    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取股票行情"""
        source = self._get_tencent_source()
        return source.get_batch_quotes(codes)

    def is_trading_time(self) -> bool:
        """判断是否交易时间"""
        return is_trading_time()

    def _get_tencent_source(self):
        """获取腾讯数据源"""
        if self._tencent_source is None:
            from backend.market.cn.sources.tencent import TencentSource
            self._tencent_source = TencentSource()
        return self._tencent_source

    def get_today_limit_ups(self) -> List[Dict]:
        """获取今日涨停股票"""
        source = self._get_tencent_source()
        return source.get_limit_ups()
