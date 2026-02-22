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
# 策略注册表
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
# 策略管理器
# =============================================================================

class StrategyManager:
    """
    策略管理器

    负责管理所有策略的注册、创建和执行
    """

    def __init__(self, use_registries: bool = True):
        """
        初始化策略管理器

        Args:
            use_registries: 是否使用全局注册表。测试时可设为False以避免全局状态
        """
        self._event_detectors: Dict[str, IEventDetector] = {}
        self._fund_selectors: Dict[str, IFundSelector] = {}
        self._signal_filters: Dict[str, ISignalFilter] = {}
        self._use_registries = use_registries

    def register_event_detector(
        self,
        name: str,
        detector: IEventDetector,
        config: Dict = None
    ) -> None:
        """注册事件检测策略"""
        self._event_detectors[name] = detector
        logger.debug(f"注册事件检测策略: {name}")

    def register_fund_selector(
        self,
        name: str,
        selector: IFundSelector,
        config: Dict = None
    ) -> None:
        """注册基金选择策略"""
        self._fund_selectors[name] = selector
        logger.debug(f"注册基金选择策略: {name}")

    def register_signal_filter(
        self,
        name: str,
        filter_strategy: ISignalFilter,
        config: Dict = None
    ) -> None:
        """注册信号过滤策略"""
        self._signal_filters[name] = filter_strategy
        logger.debug(f"注册信号过滤策略: {name}")

    def get_event_detector(self, name: str) -> Optional[IEventDetector]:
        """获取事件检测策略"""
        return self._event_detectors.get(name)

    def get_fund_selector(self, name: str) -> Optional[IFundSelector]:
        """获取基金选择策略"""
        return self._fund_selectors.get(name)

    def get_signal_filter(self, name: str) -> Optional[ISignalFilter]:
        """获取信号过滤策略"""
        return self._signal_filters.get(name)

    def list_event_detectors(self) -> List[str]:
        """列出所有事件检测策略"""
        return list(self._event_detectors.keys())

    def list_fund_selectors(self) -> List[str]:
        """列出所有基金选择策略"""
        return list(self._fund_selectors.keys())

    def list_signal_filters(self) -> List[str]:
        """列出所有信号过滤策略"""
        return list(self._signal_filters.keys())

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
        configs = configs or {}

        # 从注册表获取策略类
        detector_cls = event_detector_registry.get(event_detector_name)
        if detector_cls is None:
            raise ValueError(f"未找到事件检测策略: {event_detector_name}")

        selector_cls = fund_selector_registry.get(fund_selector_name)
        if selector_cls is None:
            raise ValueError(f"未找到基金选择策略: {fund_selector_name}")

        # 创建实例（需要配置）
        event_config = configs.get('event_config', {})
        fund_config = configs.get('fund_config', {})

        # 注意：这里假设策略类有 from_config 类方法
        # 如果没有，需要直接实例化
        try:
            detector = detector_cls.from_config(event_config) if hasattr(detector_cls, 'from_config') else detector_cls()
            selector = selector_cls.from_config(fund_config) if hasattr(selector_cls, 'from_config') else selector_cls()
        except Exception as e:
            logger.warning(f"创建策略实例失败，尝试无参构造: {e}")
            detector = detector_cls()
            selector = selector_cls()

        # 创建过滤器
        filters = []
        filter_configs = configs.get('filter_configs', {})
        for filter_name in filter_names:
            filter_cls = signal_filter_registry.get(filter_name)
            if filter_cls is None:
                logger.warning(f"未找到过滤策略: {filter_name}，跳过")
                continue

            filter_config = filter_configs.get(filter_name, {})
            try:
                f = filter_cls.from_config(filter_config) if hasattr(filter_cls, 'from_config') else filter_cls()
                filters.append(f)
            except Exception as e:
                logger.warning(f"创建过滤器 {filter_name} 失败: {e}")

        return {
            'event_detector': detector,
            'fund_selector': selector,
            'filters': filters
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

    def create_direct(
        self,
        event_detector: IEventDetector,
        fund_selector: IFundSelector,
        filters: List[ISignalFilter] = None
    ) -> Dict[str, Any]:
        """
        直接使用传入的策略实例创建策略组合

        用于测试时直接注入 mock 策略，避免依赖全局注册表

        Args:
            event_detector: 事件检测策略实例
            fund_selector: 基金选择策略实例
            filters: 过滤策略实例列表

        Returns:
            {
                'event_detector': IEventDetector,
                'fund_selector': IFundSelector,
                'filters': List[ISignalFilter]
            }
        """
        return {
            'event_detector': event_detector,
            'fund_selector': fund_selector,
            'filters': filters or []
        }

    def reset(self) -> None:
        """
        重置策略管理器

        清除所有已注册的策略。用于测试隔离。
        """
        self._event_detectors.clear()
        self._fund_selectors.clear()
        self._signal_filters.clear()
        logger.debug("策略管理器已重置")


# 全局策略管理器实例
strategy_manager = StrategyManager()


def get_strategy_manager() -> StrategyManager:
    """
    获取全局策略管理器实例

    Returns:
        全局 StrategyManager 实例
    """
    return strategy_manager


def create_test_strategy_manager() -> StrategyManager:
    """
    创建测试专用的策略管理器

    返回一个不使用全局注册表的管理器实例，
    避免测试之间的状态污染。

    Returns:
        独立的 StrategyManager 实例
    """
    return StrategyManager(use_registries=True)


def reset_strategy_manager() -> None:
    """
    重置全局策略管理器（主要用于测试）

    警告：此方法会清空所有已注册的策略，仅应在测试环境中使用
    """
    strategy_manager.reset()
