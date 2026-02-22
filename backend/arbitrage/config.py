"""
套利引擎配置

定义套利引擎的行为配置，包括策略组合选择和各策略的参数。
跨市场通用，各市场引擎可设置自己的默认值。
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ArbitrageEngineConfig:
    """
    套利引擎配置

    定义套利引擎的策略组合配置：
    - 选择哪个事件检测策略
    - 选择哪个基金选择策略
    - 使用哪些信号过滤策略
    - 各策略的配置参数
    """
    # 策略选择
    event_detector: str = ""                      # 事件检测策略名称
    fund_selector: str = ""                       # 基金选择策略名称
    signal_filters: Optional[List[str]] = None    # 信号过滤策略名称列表

    # 策略参数配置
    event_config: Optional[Dict] = None           # 事件检测策略参数
    fund_config: Optional[Dict] = None            # 基金选择策略参数
    filter_configs: Optional[Dict] = None         # 过滤策略参数 {name: config}

    def __post_init__(self):
        if self.signal_filters is None:
            self.signal_filters = []
        if self.event_config is None:
            self.event_config = {}
        if self.fund_config is None:
            self.fund_config = {}
        if self.filter_configs is None:
            self.filter_configs = {}

    @classmethod
    def from_dict(cls, data: Dict) -> 'ArbitrageEngineConfig':
        """从字典创建配置"""
        return cls(
            event_detector=data.get("event_detector", ""),
            fund_selector=data.get("fund_selector", ""),
            signal_filters=data.get("signal_filters", []),
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
