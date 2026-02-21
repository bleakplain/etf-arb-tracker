"""
策略包 - 套利策略的可插拔实现

本包包含所有套利策略的可插拔实现，按功能模块组织：
- event_detectors: 事件检测策略（涨停/突破/逼空等）
- fund_selectors: 基金选择策略（权重/流动性/溢价等）
- signal_filters: 信号过滤策略（时间/流动性/风险等）

使用方式：
1. 实现策略接口（IEventDetectorStrategy/IFundSelectionStrategy/ISignalFilterStrategy）
2. 使用装饰器注册到对应的注册表
3. 在配置文件中指定使用哪个策略

示例：
    @event_detector_registry.register("my_detector")
    class MyDetector(IEventDetectorStrategy):
        pass
"""

from backend.core.strategy_registry import (
    event_detector_registry,
    fund_selector_registry,
    signal_filter_registry,
    strategy_manager
)

__all__ = [
    'event_detector_registry',
    'fund_selector_registry',
    'signal_filter_registry',
    'strategy_manager',
]
