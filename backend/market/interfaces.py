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


class IETFHoldingProvider(ABC):
    """ETF持仓数据提供接口"""

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


# =============================================================================
# HTTP客户端接口 - 用于抽象外部API调用
# =============================================================================

@dataclass
class HTTPResponse:
    """HTTP响应"""
    status_code: int
    text: str
    encoding: str = "utf-8"

    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status_code == 200


class IHTTPClient(ABC):
    """
    HTTP客户端接口

    用于抽象HTTP请求，便于测试时mock
    """

    @abstractmethod
    def get(self, url: str, headers: Dict[str, str] = None, timeout: int = 10) -> HTTPResponse:
        """
        发送GET请求

        Args:
            url: 请求URL
            headers: 请求头
            timeout: 超时时间（秒）

        Returns:
            HTTPResponse对象
        """
        pass
