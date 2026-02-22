"""
A股行情数据获取
"""

from typing import List, Dict, Optional

from backend.market.interfaces import IQuoteFetcher


class CNQuoteFetcher(IQuoteFetcher):
    """A股行情数据获取器"""

    def __init__(self):
        self._tencent_source = None

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
        from datetime import datetime, time

        now = datetime.now()
        if now.weekday() >= 5:
            return False

        current_time = now.time()
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)

        return (morning_start <= current_time <= morning_end or
                afternoon_start <= current_time <= afternoon_end)

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
