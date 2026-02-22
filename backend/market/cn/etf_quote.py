"""
A股ETF行情数据获取
"""

from typing import Optional, Dict
from loguru import logger


class CNETFQuoteFetcher:
    """A股ETF行情获取器"""

    def __init__(self):
        self._source = None

    def _get_source(self):
        """获取数据源"""
        if self._source is None:
            from backend.market.cn.sources.tencent import TencentSource
            self._source = TencentSource()
        return self._source

    def get_etf_quote(self, code: str) -> Optional[Dict]:
        """获取ETF行情"""
        source = self._get_source()
        return source.get_etf_quote(code)

    def get_etf_batch_quotes(self, codes: list) -> Dict[str, Optional[Dict]]:
        """批量获取ETF行情"""
        source = self._get_source()
        return source.get_etf_batch_quotes(codes)

    def check_liquidity(self, etf_code: str, min_amount: float = 50000000) -> bool:
        """检查ETF流动性"""
        quote = self.get_etf_quote(etf_code)
        if not quote:
            return False
        current_amount = quote.get('amount', 0)
        return current_amount >= min_amount / 4
