"""
套利引擎配置

定义套利引擎的行为配置，包括策略组合选择和各策略的参数。
跨市场通用，各市场引擎可设置自己的默认值。
"""

from typing import Tuple
from dataclasses import dataclass, field
from loguru import logger


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
    signal_filters: list[str] = field(default_factory=list)  # 信号过滤策略名称列表

    # 策略参数配置
    event_config: dict = field(default_factory=dict)  # 事件检测策略参数
    fund_config: dict = field(default_factory=dict)    # 基金选择策略参数
    filter_configs: dict = field(default_factory=dict)  # 过滤策略参数 {name: config}

    @classmethod
    def from_dict(cls, data: dict) -> 'ArbitrageEngineConfig':
        """从字典创建配置"""
        return cls(
            event_detector=data.get("event_detector", ""),
            fund_selector=data.get("fund_selector", ""),
            signal_filters=data.get("signal_filters", []),
            event_config=data.get("event_config", {}),
            fund_config=data.get("fund_config", {}),
            filter_configs=data.get("filter_configs", {})
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "event_detector": self.event_detector,
            "fund_selector": self.fund_selector,
            "signal_filters": self.signal_filters,
            "event_config": self.event_config,
            "fund_config": self.fund_config,
            "filter_configs": self.filter_configs
        }

    def validate(self) -> tuple[bool, list[str]]:
        """
        验证配置是否有效

        检查策略名称是否在注册表中存在。

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # 导入注册表（延迟导入避免循环依赖）
        from backend.arbitrage.strategy_registry import (
            event_detector_registry,
            fund_selector_registry,
            signal_filter_registry,
        )

        # 验证事件检测策略
        if not self.event_detector:
            errors.append("event_detector 不能为空")
        elif not event_detector_registry.is_registered(self.event_detector):
            available = event_detector_registry.list_names()
            errors.append(
                f"event_detector '{self.event_detector}' 未注册。"
                f"可用策略: {', '.join(available) if available else '(无)'}"
            )

        # 验证基金选择策略
        if not self.fund_selector:
            errors.append("fund_selector 不能为空")
        elif not fund_selector_registry.is_registered(self.fund_selector):
            available = fund_selector_registry.list_names()
            errors.append(
                f"fund_selector '{self.fund_selector}' 未注册。"
                f"可用策略: {', '.join(available) if available else '(无)'}"
            )

        # 验证信号过滤策略
        for filter_name in self.signal_filters:
            if not signal_filter_registry.is_registered(filter_name):
                available = signal_filter_registry.list_names()
                errors.append(
                    f"signal_filter '{filter_name}' 未注册。"
                    f"可用策略: {', '.join(available) if available else '(无)'}"
                )

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(f"配置验证失败: {'; '.join(errors)}")

        return is_valid, errors

    def assert_valid(self) -> None:
        """
        断言配置有效，无效时抛出异常

        Raises:
            ValueError: 配置无效时
        """
        is_valid, errors = self.validate()
        if not is_valid:
            raise ValueError(
                f"ArbitrageEngineConfig 验证失败:\n" +
                "\n".join(f"  - {e}" for e in errors)
            )
