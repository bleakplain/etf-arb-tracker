"""
市场数据接口 - 跨市场通用
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from datetime import time


class IQuoteFetcher(ABC):
    """行情数据获取接口"""

    @abstractmethod
    def get_stock_quote(self, code: str) -> Optional[Dict]:
        """
        获取单个股票行情

        Args:
            code: 股票代码（6位数字）

        Returns:
            行情数据字典，包含以下字段:
            - code: 股票代码
            - name: 股票名称
            - price: 当前价格
            - change_pct: 涨跌幅
            - volume: 成交量
            - amount: 成交额
            - timestamp: 时间戳
            如果获取失败返回None
        """
        pass

    @abstractmethod
    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """
        批量获取股票行情

        Args:
            codes: 股票代码列表

        Returns:
            股票代码到行情数据的字典，获取失败的股票对应值为None
        """
        pass

    @abstractmethod
    def is_trading_time(self) -> bool:
        """判断是否交易时间"""
        pass


class IETFHoldingProvider(ABC):
    """ETF持仓数据提供接口"""

    @abstractmethod
    def get_etf_top_holdings(self, etf_code: str) -> Optional[Dict]:
        """
        获取ETF前十大持仓

        Args:
            etf_code: ETF代码

        Returns:
            持仓数据字典，包含:
            - etf_code: ETF代码
            - etf_name: ETF名称
            - top_holdings: 前十大持仓列表
                - stock_code: 股票代码
                - stock_name: 股票名称
                - weight: 权重
            - total_weight: 总权重
            如果获取失败返回None
        """
        pass

    def load_mapping(self, filepath: str) -> Optional[Dict]:
        """
        加载证券-ETF映射关系

        Args:
            filepath: 映射文件路径

        Returns:
            股票代码到ETF列表的映射字典，失败返回None
        """
        pass

    def save_mapping(self, mapping: Dict, filepath: str) -> None:
        """
        保存证券-ETF映射关系

        Args:
            mapping: 映射数据字典
            filepath: 保存路径
        """
        pass

    def build_stock_etf_mapping(
        self,
        stock_codes: List[str],
        etf_codes: List[str]
    ) -> Dict:
        """
        构建证券-ETF映射关系

        Args:
            stock_codes: 股票代码列表
            etf_codes: ETF代码列表

        Returns:
            股票代码到ETF列表的映射字典
        """
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
    def get(
        self,
        url: str,
        headers: Dict[str, str] = None,
        timeout: int = 10
    ) -> HTTPResponse:
        """
        发送GET请求

        Args:
            url: 请求URL
            headers: 请求头字典
            timeout: 超时时间（秒）

        Returns:
            HTTPResponse对象，包含:
            - status_code: HTTP状态码
            - text: 响应内容
            - encoding: 编码
        """
        pass
