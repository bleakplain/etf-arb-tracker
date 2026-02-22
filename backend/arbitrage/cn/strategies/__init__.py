"""A股策略包

提供A股市场专用的套利策略：
- 事件检测：涨停检测
- 基金选择：权重优先、流动性优先、溢价优先、综合评估
- 信号过滤：时间过滤、流动性过滤、风险过滤
"""

from backend.arbitrage.cn.strategies.interfaces import (
    IEventDetector,
    IFundSelector,
    ISignalFilter,
)

__all__ = [
    'IEventDetector',
    'IFundSelector',
    'ISignalFilter',
]
