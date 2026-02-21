"""
监控包

包含系统的监控和编排组件：
- LimitUpMonitor: A股涨停监控器（协调策略引擎）
- create_monitor_with_defaults: 工厂函数

架构说明：
- 本模块属于编排层(Orchestration Layer)
- 依赖: domain, data, strategy, engine
- 被: api 层依赖
"""

from backend.monitor.limit_monitor import LimitUpMonitor, create_monitor_with_defaults

__all__ = [
    'LimitUpMonitor',
    'create_monitor_with_defaults',
]
