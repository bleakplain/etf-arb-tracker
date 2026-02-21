"""
策略接口定义

定义套利策略的可插拔接口，支持：
1. 事件检测策略（涨停/突破/逼空等）
2. 基金选择策略（权重/流动性/溢价等）
3. 信号过滤策略（时间/流动性/风险等）

这样设计后，新增套利策略只需实现接口并注册，无需修改核心代码。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from backend.arbitrage.domain.models import TradingSignal
from backend.market.domain.models import LimitUpStock
from backend.market.domain import ETFReference, ETFCategory


@dataclass
class EventInfo:
    """
    市场事件信息

    表示检测到的市场事件，如涨停、突破、逼空等
    """
    event_type: str           # 事件类型: limit_up, breakout, short_squeeze等
    security_code: str        # 证券代码
    security_name: str        # 证券名称
    price: float              # 当前价格
    change_pct: float         # 涨跌幅
    trigger_price: float      # 触发价格
    trigger_time: str         # 触发时间
    volume: float = 0         # 成交量
    amount: float = 0         # 成交额
    metadata: Dict = None     # 额外元数据

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'event_type': self.event_type,
            'security_code': self.security_code,
            'security_name': self.security_name,
            'price': self.price,
            'change_pct': self.change_pct,
            'trigger_price': self.trigger_price,
            'trigger_time': self.trigger_time,
            'volume': self.volume,
            'amount': self.amount,
            'metadata': self.metadata
        }


class IEventDetectorStrategy(ABC):
    """
    事件检测策略接口

    职责：检测市场中的套利机会事件
    示例：
    - LimitUpEventDetector: 检测涨停事件
    - BreakoutEventDetector: 检测突破事件
    - ShortSqueezeEventDetector: 检测逼空事件
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称"""
        pass

    @abstractmethod
    def detect(self, quote: Dict) -> Optional[EventInfo]:
        """
        检测单个证券的市场事件

        Args:
            quote: 行情数据字典

        Returns:
            检测到的事件信息，未检测到返回None
        """
        pass

    @abstractmethod
    def is_valid(self, event: EventInfo) -> bool:
        """
        验证事件是否有效

        Args:
            event: 事件信息

        Returns:
            是否符合策略要求
        """
        pass


class IFundSelectionStrategy(ABC):
    """
    基金选择策略接口

    职责：从符合条件的基金中选择最优的
    示例：
    - HighestWeightStrategy: 选择权重最高的
    - BestLiquidityStrategy: 选择流动性最好的
    - LowestPremiumStrategy: 选择溢价最低的
    - BalancedStrategy: 综合评估选择
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称"""
        pass

    @abstractmethod
    def select(
        self,
        eligible_funds: List[ETFReference],
        event: EventInfo
    ) -> Optional[ETFReference]:
        """
        从符合条件的基金中选择最优的

        Args:
            eligible_funds: 符合条件的基金列表
            event: 触发的事件信息

        Returns:
            选中的基金，无不返回None
        """
        pass

    @abstractmethod
    def get_selection_reason(self, fund: ETFReference) -> str:
        """
        获取选择原因说明

        Args:
            fund: 选中的基金

        Returns:
            选择原因的文字说明
        """
        pass


class ISignalFilterStrategy(ABC):
    """
    信号过滤策略接口

    职责：过滤不符合条件的信号
    示例：
    - TimeFilterStrategy: 时间过滤（距收盘时间）
    - LiquidityFilterStrategy: 流动性过滤
    - RiskFilterStrategy: 风险过滤
    - ConfidentFilterStrategy: 置信度过滤
    """

    @property
    @abstractmethod
    def filter_name(self) -> str:
        """过滤器名称"""
        pass

    @abstractmethod
    def should_filter(
        self,
        event: EventInfo,
        fund: ETFReference,
        signal: TradingSignal
    ) -> tuple[bool, str]:
        """
        判断是否过滤该信号

        Args:
            event: 触发事件
            fund: 选择的基金
            signal: 生成的信号

        Returns:
            (should_filter, reason) - (是否过滤, 过滤原因)
        """
        pass

    @property
    @abstractmethod
    def is_required(self) -> bool:
        """
        是否为必需过滤器

        必需过滤器失败时会拒绝整个信号，
        非必需过滤器仅记录警告
        """
        pass


class IStrategyConfig(ABC):
    """
    策略配置接口

    职责：定义策略的配置参数
    """

    @abstractmethod
    def to_dict(self) -> Dict:
        """转换为字典"""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict) -> 'IStrategyConfig':
        """从字典创建配置"""
        pass


@dataclass
class StrategyChainConfig:
    """
    策略链配置

    定义完整的套利策略链
    """
    # 事件检测策略
    event_detector: str = "limit_up"  # limit_up, breakout, short_squeeze

    # 基金选择策略
    fund_selector: str = "highest_weight"  # highest_weight, best_liquidity, lowest_premium

    # 信号过滤策略列表（按顺序执行）
    signal_filters: List[str] = None  # time_filter, liquidity_filter等

    # 各策略的配置参数
    event_config: Dict = None
    fund_config: Dict = None
    filter_configs: Dict = None

    def __post_init__(self):
        if self.signal_filters is None:
            self.signal_filters = ["time_filter", "liquidity_filter"]
        if self.event_config is None:
            self.event_config = {}
        if self.fund_config is None:
            self.fund_config = {}
        if self.filter_configs is None:
            self.filter_configs = {}

    @classmethod
    def from_dict(cls, data: Dict) -> 'StrategyChainConfig':
        """从字典创建配置"""
        return cls(
            event_detector=data.get("event_detector", "limit_up"),
            fund_selector=data.get("fund_selector", "highest_weight"),
            signal_filters=data.get("signal_filters", ["time_filter", "liquidity_filter"]),
            event_config=data.get("event_config", {}),
            fund_config=data.get("fund_config", {}),
            filter_configs=data.get("filter_configs", {})
        )

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "event_detector": self.event_detector,
            "fund_selector": self.fund_selector,
            "signal_filters": self.signal_filters,
            "event_config": self.event_config,
            "fund_config": self.fund_config,
            "filter_configs": self.filter_configs
        }
