"""
策略注册表系统

为套利策略提供插件注册表，支持：
- 事件检测策略 (IEventDetector)
- 基金选择策略 (IFundSelector)
- 信号过滤策略 (ISignalFilter)

与 plugin_registry.py 配合使用，实现策略的可插拔扩展。
"""

from typing import Dict, List, Optional, Any, Tuple
from loguru import logger

from backend.utils.plugin_registry import PluginRegistry
from backend.arbitrage.cn.strategies.interfaces import (
    IEventDetector,
    IFundSelector,
    ISignalFilter,
)
from backend.market.events import MarketEvent
from backend.market import CandidateETF
from backend.arbitrage.models import TradingSignal


# =============================================================================
# 策略注册表（全局单例）
# =============================================================================

# 事件检测策略注册表
event_detector_registry = PluginRegistry(
    "EventDetector",
    base_class=IEventDetector
)

# 基金选择策略注册表
fund_selector_registry = PluginRegistry(
    "FundSelector",
    base_class=IFundSelector
)

# 信号过滤策略注册表
signal_filter_registry = PluginRegistry(
    "SignalFilter",
    base_class=ISignalFilter
)


# =============================================================================
# 策略管理器（简化的门面模式）
# =============================================================================

class StrategyManager:
    """
    策略管理器 - 简化版

    直接使用全局注册表，不维护自己的副本。
    提供便捷的方法来创建和验证策略组合。
    """

    def __init__(self, use_registries: bool = True):
        """
        初始化策略管理器

        Args:
            use_registries: 是否使用全局注册表。测试时可设为False以避免全局状态
        """
        self._use_registries = use_registries

    def create_from_registry(
        self,
        event_detector_name: str,
        fund_selector_name: str,
        filter_names: List[str],
        configs: Dict = None
    ) -> Dict[str, Any]:
        """
        从注册表创建策略实例

        Args:
            event_detector_name: 事件检测策略名称
            fund_selector_name: 基金选择策略名称
            filter_names: 过滤策略名称列表
            configs: 策略配置

        Returns:
            {
                'event_detector': IEventDetector,
                'fund_selector': IFundSelector,
                'filters': List[ISignalFilter]
            }
        """
        if self._use_registries:
            configs = configs or {}

            # 创建事件检测器
            event_config = configs.get('event_config', {})
            detector = event_detector_registry.create_from_config(
                event_detector_name,
                event_config
            )
            if detector is None:
                raise ValueError(f"未找到事件检测策略: {event_detector_name}")

            # 创建基金选择器
            fund_config = configs.get('fund_config', {})
            selector = fund_selector_registry.create_from_config(
                fund_selector_name,
                fund_config
            )
            if selector is None:
                raise ValueError(f"未找到基金选择策略: {fund_selector_name}")

            # 创建过滤器
            filters = []
            filter_configs = configs.get('filter_configs', {})
            for filter_name in filter_names:
                filter_config = filter_configs.get(filter_name, {})
                f = signal_filter_registry.create_from_config(filter_name, filter_config)
                if f is not None:
                    filters.append(f)
                else:
                    logger.warning(f"未找到过滤策略: {filter_name}，跳过")

            return {
                'event_detector': detector,
                'fund_selector': selector,
                'filters': filters
            }
        else:
            # 测试模式：返回空策略组合（测试应该自己设置模拟对象）
            return {
                'event_detector': None,
                'fund_selector': None,
                'filters': []
            }

    def validate_strategy_combination(
        self,
        event_detector: str,
        fund_selector: str,
        filters: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        验证策略组合是否完整

        Args:
            event_detector: 事件检测策略名称
            fund_selector: 基金选择策略名称
            filters: 过滤策略名称列表

        Returns:
            (is_valid, error_messages)
        """
        if not self._use_registries:
            return True, []

        errors = []

        if not event_detector_registry.is_registered(event_detector):
            errors.append(f"事件检测策略 '{event_detector}' 未注册")

        if not fund_selector_registry.is_registered(fund_selector):
            errors.append(f"基金选择策略 '{fund_selector}' 未注册")

        for filter_name in filters:
            if not signal_filter_registry.is_registered(filter_name):
                errors.append(f"过滤策略 '{filter_name}' 未注册")

        return len(errors) == 0, errors

    def get_strategy_summary(self) -> Dict:
        """
        获取策略摘要

        Returns:
            {
                'event_detectors': {name: metadata},
                'fund_selectors': {name: metadata},
                'signal_filters': {name: metadata}
            }
        """
        if not self._use_registries:
            return {'event_detectors': {}, 'fund_selectors': {}, 'signal_filters': {}}

        return {
            'event_detectors': {
                name: event_detector_registry.get_metadata(name)
                for name in event_detector_registry.list_names()
            },
            'fund_selectors': {
                name: fund_selector_registry.get_metadata(name)
                for name in fund_selector_registry.list_names()
            },
            'signal_filters': {
                name: signal_filter_registry.get_metadata(name)
                for name in signal_filter_registry.list_names()
            }
        }

    def reset(self):
        """重置所有注册表（主要用于测试）"""
        event_detector_registry.clear()
        fund_selector_registry.clear()
        signal_filter_registry.clear()
        logger.debug("策略管理器已重置")


# =============================================================================
# 全局策略管理器实例
# =============================================================================

strategy_manager = StrategyManager()


# =============================================================================
# 便捷函数（向后兼容）
# =============================================================================

def create_strategies(
    event_detector_name: str,
    fund_selector_name: str,
    filter_names: List[str],
    configs: Dict = None
) -> Dict[str, Any]:
    """
    从注册表创建策略实例（便捷函数）

    Args:
        event_detector_name: 事件检测策略名称
        fund_selector_name: 基金选择策略名称
        filter_names: 过滤策略名称列表
        configs: 策略配置

    Returns:
        策略实例字典
    """
    return strategy_manager.create_from_registry(
        event_detector_name,
        fund_selector_name,
        filter_names,
        configs
    )


def validate_strategy_combination(
    event_detector: str,
    fund_selector: str,
    filters: List[str]
) -> Tuple[bool, List[str]]:
    """
    验证策略组合（便捷函数）

    Args:
        event_detector: 事件检测策略名称
        fund_selector: 基金选择策略名称
        filters: 过滤策略名称列表

    Returns:
        (is_valid, error_messages)
    """
    return strategy_manager.validate_strategy_combination(
        event_detector,
        fund_selector,
        filters
    )


def list_strategies() -> Dict:
    """
    列出所有策略（便捷函数）

    Returns:
        策略摘要字典
    """
    return strategy_manager.get_strategy_summary()


def reset_strategy_manager():
    """
    重置策略管理器（用于测试）

    重置所有注册表的状态，主要用于测试隔离。
    """
    strategy_manager.reset()


def create_test_strategy_manager() -> StrategyManager:
    """
    创建测试用策略管理器

    返回一个不使用全局注册表的策略管理器实例，
    用于测试隔离。

    Returns:
        独立的策略管理器实例
    """
    return StrategyManager(use_registries=False)
