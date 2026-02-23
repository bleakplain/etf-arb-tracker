"""
涨停股票数据获取器

提供A股涨停股票的查询功能
"""

from typing import List, Dict, Optional
from loguru import logger

from backend.market.cn.quote_fetcher import CNQuoteFetcher


class LimitUpStocksFetcher:
    """涨停股票数据获取器"""

    def __init__(self, quote_fetcher: Optional[CNQuoteFetcher] = None):
        self.quote_fetcher = quote_fetcher or CNQuoteFetcher()

    def get_today_limit_ups(self, stock_df=None) -> List[Dict]:
        """
        获取今日涨停股票列表

        Args:
            stock_df: 可选的股票数据DataFrame（用于缓存）

        Returns:
            涨停股票列表
        """
        # 如果提供了stock_df，从其中筛选涨停股
        if stock_df is not None:
            return self._filter_limit_ups_from_df(stock_df)

        # 否则使用默认方法
        try:
            limit_ups = self.quote_fetcher.get_today_limit_ups()
            return limit_ups if limit_ups else []
        except Exception as e:
            logger.error(f"获取涨停股票失败: {e}")
            return []

    def _filter_limit_ups_from_df(self, stock_df) -> List[Dict]:
        """从DataFrame中筛选涨停股票"""
        results = []
        try:
            from backend.utils.constants import CNMarketConstants
            threshold = CNMarketConstants.DEFAULT_LIMIT_UP_THRESHOLD

            for _, row in stock_df.iterrows():
                if row.get('change_pct', 0) >= threshold:
                    results.append({
                        'code': row.get('code', ''),
                        'name': row.get('name', ''),
                        'price': row.get('price', 0),
                        'change_pct': row.get('change_pct', 0),
                        'volume': row.get('volume', 0),
                        'amount': row.get('amount', 0),
                        'turnover': row.get('turnover', 0),
                        'limit_time': row.get('limit_time', ''),
                        'locked_amount': row.get('locked_amount', 0)
                    })
        except Exception as e:
            logger.error(f"筛选涨停股票失败: {e}")

        return results
