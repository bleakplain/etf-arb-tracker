"""
港股行情数据获取（框架）
"""

from typing import List, Dict, Optional
from backend.market.interfaces import IQuoteFetcher


class HKQuoteFetcher(IQuoteFetcher):
    """港股行情数据获取器（框架）"""

    def get_stock_quote(self, code: str) -> Optional[Dict]:
        """获取单个股票行情（待实现）"""
        raise NotImplementedError("港股行情获取待实现")

    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取股票行情（待实现）"""
        raise NotImplementedError("港股行情获取待实现")

    def is_trading_time(self) -> bool:
        """判断是否港股交易时间"""
        return False
