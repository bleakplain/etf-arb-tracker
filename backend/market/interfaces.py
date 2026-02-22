"""
市场数据接口 - 跨市场通用
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass


class IQuoteFetcher(ABC):
    """行情数据获取接口"""

    @abstractmethod
    def get_stock_quote(self, code: str) -> Optional[Dict]:
        """获取单个股票行情"""
        pass

    @abstractmethod
    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取股票行情"""
        pass

    @abstractmethod
    def is_trading_time(self) -> bool:
        """判断是否交易时间"""
        pass


class IHoldingProvider(ABC):
    """持仓数据提供接口"""

    @abstractmethod
    def get_etf_top_holdings(self, etf_code: str) -> Optional[Dict]:
        """获取ETF前十大持仓"""
        pass

    def load_mapping(self, filepath: str) -> Optional[Dict]:
        """加载证券-ETF映射关系"""
        pass

    def save_mapping(self, mapping: Dict, filepath: str) -> None:
        """保存证券-ETF映射关系"""
        pass

    def build_stock_etf_mapping(self, stock_codes: List[str], etf_codes: List[str]) -> Dict:
        """构建证券-ETF映射关系"""
        pass
