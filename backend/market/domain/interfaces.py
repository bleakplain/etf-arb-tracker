"""市场领域接口"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from backend.market.domain.models import ETF, Holding


class IQuoteFetcher(ABC):
    """行情获取器接口"""

    @abstractmethod
    def get_quote(self, code: str) -> Optional[Dict]:
        """获取单个标的信息"""
        pass

    @abstractmethod
    def list_quotes(self, codes: List[str]) -> Dict[str, Dict]:
        """批量获取行情"""
        pass

    @abstractmethod
    def is_trading_time(self) -> bool:
        """判断是否交易时间"""
        pass


class IHoldingProvider(ABC):
    """ETF持仓数据提供者接口"""

    @abstractmethod
    def get_etf(self, etf_code: str) -> Optional[ETF]:
        """获取ETF实体（含持仓）"""
        pass

    @abstractmethod
    def list_etfs(self, etf_codes: List[str]) -> List[ETF]:
        """批量获取ETF"""
        pass

    @abstractmethod
    def find_etfs_by_stock(self, stock_code: str) -> List[ETF]:
        """查找包含指定股票的ETF"""
        pass
