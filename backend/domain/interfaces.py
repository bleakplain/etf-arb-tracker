"""
领域接口定义

定义所有业务接口，遵循依赖倒置原则：
- 高层模块依赖接口，不依赖具体实现
- 具体实现依赖接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional

from .value_objects import TradingSignal


class IQuoteFetcher(ABC):
    """行情数据获取接口"""

    @abstractmethod
    def get_stock_quote(self, stock_code: str) -> Optional[Dict]:
        """
        获取单只股票实时行情

        Args:
            stock_code: 股票代码

        Returns:
            行情字典，未找到返回None
        """

    @abstractmethod
    def get_batch_quotes(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取股票行情

        Args:
            stock_codes: 股票代码列表

        Returns:
            {股票代码: 行情数据}
        """

    @abstractmethod
    def is_trading_time(self) -> bool:
        """判断是否在交易时间内"""

    @abstractmethod
    def get_time_to_close(self) -> int:
        """
        获取距离收盘的秒数

        Returns:
            距离15:00收盘的秒数，不在交易时间返回-1
        """


class IETFHolderProvider(ABC):
    """ETF持仓关系提供者接口"""

    @abstractmethod
    def load_mapping(self, filepath: str) -> Optional[Dict]:
        """加载股票-ETF映射关系"""

    @abstractmethod
    def save_mapping(self, mapping: Dict, filepath: str = None) -> None:
        """保存股票-ETF映射关系"""

    @abstractmethod
    def build_stock_etf_mapping(
        self,
        stock_codes: List[str],
        etf_codes: List[str]
    ) -> Dict:
        """构建股票-ETF映射关系"""


class IETFHoldingsProvider(ABC):
    """ETF持仓详情提供者接口"""

    @abstractmethod
    def get_etf_top_holdings(self, etf_code: str) -> Dict:
        """
        获取ETF前十大持仓

        Returns:
            {
                'etf_code': str,
                'etf_name': str,
                'top_holdings': [{'stock_code': str, 'stock_name': str, 'weight': float}],
                'total_weight': float
            }
        """


class IETFQuoteProvider(ABC):
    """ETF行情提供者接口"""

    @abstractmethod
    def get_etf_quote(self, etf_code: str) -> Optional[Dict]:
        """获取单只ETF行情"""

    @abstractmethod
    def get_etf_batch_quotes(self, etf_codes: List[str]) -> Dict[str, Dict]:
        """批量获取ETF行情"""

    @abstractmethod
    def check_liquidity(self, etf_code: str, min_amount: float) -> bool:
        """检查ETF流动性"""


class ISignalEvaluator(ABC):
    """信号评估器接口"""

    @abstractmethod
    def evaluate(self, limit_info: Dict, etf_info: Dict) -> tuple[str, str]:
        """
        评估信号质量

        Args:
            limit_info: 涨停股票信息
            etf_info: ETF信息

        Returns:
            (confidence, risk_level) - (置信度, 风险等级)
        """


class ISignalRepository(ABC):
    """信号仓储接口"""

    @abstractmethod
    def save(self, signal: TradingSignal) -> None:
        """保存单个信号"""

    @abstractmethod
    def save_all(self, signals: List[TradingSignal]) -> None:
        """批量保存信号"""

    @abstractmethod
    def get_today_signals(self) -> List[TradingSignal]:
        """获取今天的所有信号"""

    @abstractmethod
    def get_recent_signals(self, limit: int = 20) -> List[TradingSignal]:
        """获取最近的信号"""


class ISignalSender(ABC):
    """信号发送器接口"""

    @abstractmethod
    def send_signal(self, signal: TradingSignal) -> bool:
        """
        发送信号通知

        Returns:
            是否发送成功
        """
