"""
ETF持仓数据获取器

提供ETF前十大持仓和分类信息
"""

from typing import Dict, List, Optional
from loguru import logger

from backend.market.cn.etf_holding_provider import CNETFHoldingProvider
from backend.market.cn.quote_fetcher import CNQuoteFetcher


class ETFHoldingsFetcher:
    """ETF持仓数据获取器"""

    def __init__(self):
        self.holding_provider = CNETFHoldingProvider()
        self.quote_fetcher = CNQuoteFetcher()

    def get_etf_top_holdings(self, etf_code: str) -> Dict:
        """
        获取ETF前十大持仓

        Args:
            etf_code: ETF代码

        Returns:
            持仓数据字典
        """
        holdings = self.holding_provider.get_etf_top_holdings(etf_code)
        if not holdings:
            return {
                'etf_code': etf_code,
                'etf_name': f'ETF{etf_code}',
                'top_holdings': [],
                'total_weight': 0
            }

        return {
            'etf_code': etf_code,
            'etf_name': holdings.get('etf_name', f'ETF{etf_code}'),
            'top_holdings': holdings.get('top_holdings', []),
            'total_weight': holdings.get('total_weight', 0)
        }

    def get_all_etfs_by_category(self) -> Dict:
        """
        获取所有ETF按分类

        Returns:
            ETF分类数据
        """
        # 暂时返回基本分类
        return {
            'broad_index': [],
            'sector': [],
            'theme': [],
            'strategy': [],
            'other': []
        }
