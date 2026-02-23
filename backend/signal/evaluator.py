"""
信号评估器模块
使用策略模式实现不同的信号评估策略

支持插件式扩展：通过装饰器注册新的评估器
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, Type, Optional
from datetime import datetime

from config.strategy import (
    SignalEvaluationConfig,
    ConservativeEvaluationConfig,
    AggressiveEvaluationConfig
)
from backend.signal.interfaces import ISignalEvaluator
from backend.utils.plugin_registry import evaluator_registry
from backend.utils.clock import Clock, SystemClock, CHINA_TZ
from backend.utils.constants import HIGH_RISK_TIME_THRESHOLD


class SignalEvaluator(ISignalEvaluator, ABC):
    """
    信号评估器基类

    所有自定义评估器应继承此类并使用 @evaluator_registry.register() 装饰器注册。

    Example:
        @evaluator_registry.register("custom", priority=50, description="My custom evaluator")
        class MyCustomEvaluator(SignalEvaluator):
            def __init__(self, config: SignalEvaluationConfig):
                self.config = config

            def evaluate(self, market_event, etf_holding) -> Tuple[str, str]:
                return "高", "低"
    """

    def __init__(self, config: SignalEvaluationConfig, clock: Optional[Clock] = None):
        self.config = config
        self._clock = clock or SystemClock()

    @abstractmethod
    def evaluate(self, market_event, etf_holding) -> Tuple[str, str]:
        """
        评估信号质量

        Args:
            market_event: 市场事件（LimitUpEvent 等）
            etf_holding: ETF持仓信息（CandidateETF）

        Returns:
            (confidence, risk_level) - (置信度, 风险等级)
        """

    def _get_time_to_close(self) -> int:
        """
        获取距离收盘的秒数

        Returns:
            距离15:00收盘的秒数，不在交易时间返回-1
        """
        now = self._clock.now(CHINA_TZ)
        close_time = now.replace(hour=15, minute=0, second=0, microsecond=0)

        if now.hour < 9 or now.hour >= 15:
            return -1

        delta = close_time - now
        return int(delta.total_seconds())


@evaluator_registry.register(
    "default",
    priority=100,
    description="默认信号评估器 - 基于权重、排名、时间等多维度评估",
    version="1.0.0"
)
class DefaultSignalEvaluator(SignalEvaluator):
    """默认信号评估器"""

    def evaluate(self, market_event, etf_holding) -> Tuple[str, str]:
        """
        评估信号质量

        评估维度：
        1. 权重越高置信度越高
        2. 排名越前置信度越高
        3. 前10持仓占比越集中风险越高
        4. 时间因素（距收盘时间）
        """
        confidence = "中"
        risk_level = "中"

        # 1. 权重评估
        weight = etf_holding.weight
        if weight >= self.config.confidence_high_weight:
            confidence = "高"
        elif weight < self.config.confidence_low_weight:
            confidence = "低"

        # 2. 排名评估
        rank = etf_holding.rank
        if rank <= self.config.confidence_high_rank and confidence != "高":
            confidence = "高"
        elif rank > self.config.confidence_low_rank:
            confidence = "低"

        # 3. 风险等级 - 时间因素
        time_to_close = self._get_time_to_close()
        if time_to_close < self.config.risk_high_time_seconds:
            risk_level = "高"
        elif time_to_close > self.config.risk_low_time_seconds:
            risk_level = "低"

        # 4. 风险等级 - 持仓集中度
        top10_ratio = etf_holding.top10_ratio
        if top10_ratio > self.config.risk_top10_ratio_high:
            if risk_level == "低":
                risk_level = "中"
            elif risk_level == "中":
                risk_level = "高"

        # 5. 涨停时间因素
        current_hour = self._clock.now(CHINA_TZ).hour
        if current_hour < self.config.risk_morning_hour:
            if risk_level == "高":
                risk_level = "中"

        return confidence, risk_level


@evaluator_registry.register(
    "conservative",
    priority=90,
    description="保守型评估器 - 更严格的评估标准",
    version="1.0.0"
)
class ConservativeEvaluator(SignalEvaluator):
    """保守型评估器 - 使用 ConservativeEvaluationConfig 配置"""

    def __init__(self, config: SignalEvaluationConfig = None, clock: Optional[Clock] = None):
        # 确保使用 ConservativeEvaluationConfig
        if config is None or isinstance(config, SignalEvaluationConfig):
            config = ConservativeEvaluationConfig()
        super().__init__(config, clock)

    def evaluate(self, market_event, etf_holding) -> Tuple[str, str]:
        """保守型评估 - 使用配置中的严格阈值"""
        weight = etf_holding.weight
        rank = etf_holding.rank

        # 使用配置的权重阈值
        if weight >= self.config.confidence_high_weight:
            confidence = "高"
        elif weight >= self.config.confidence_medium_weight:
            confidence = "中"
        else:
            confidence = "低"

        # 使用配置的排名阈值
        if rank > self.config.confidence_strict_rank:
            confidence = "低"

        # 使用配置的时间阈值
        time_to_close = self._get_time_to_close()
        if time_to_close < self.config.risk_high_time_seconds:
            risk_level = "高"
        elif time_to_close > self.config.risk_low_time_seconds:
            risk_level = "低"
        else:
            risk_level = "中"

        # 使用配置的前10持仓集中度阈值
        top10_ratio = etf_holding.top10_ratio
        if top10_ratio > self.config.risk_top10_ratio_high:
            risk_level = "高"

        return confidence, risk_level


@evaluator_registry.register(
    "aggressive",
    priority=80,
    description="激进型评估器 - 更宽松的评估标准",
    version="1.0.0"
)
class AggressiveEvaluator(SignalEvaluator):
    """激进型评估器 - 使用 AggressiveEvaluationConfig 配置"""

    def __init__(self, config: SignalEvaluationConfig = None, clock: Optional[Clock] = None):
        # 确保使用 AggressiveEvaluationConfig
        if config is None or isinstance(config, SignalEvaluationConfig):
            config = AggressiveEvaluationConfig()
        super().__init__(config, clock)

    def evaluate(self, market_event, etf_holding) -> Tuple[str, str]:
        """激进型评估 - 使用配置中的宽松阈值"""
        weight = etf_holding.weight
        rank = etf_holding.rank

        # 使用配置的权重阈值
        if weight >= self.config.confidence_high_weight:
            confidence = "高"
        elif weight >= self.config.confidence_medium_weight:
            confidence = "中"
        else:
            confidence = "低"

        # 使用配置的排名阈值
        if rank <= self.config.confidence_high_rank and confidence == "低":
            confidence = "中"
        if rank > self.config.confidence_low_rank and confidence == "高":
            confidence = "中"

        # 使用配置的时间阈值
        time_to_close = self._get_time_to_close()
        if time_to_close < self.config.risk_high_time_seconds:
            risk_level = "高"
        elif time_to_close > self.config.risk_low_time_seconds:
            risk_level = "低"
        else:
            risk_level = "中"

        # 使用配置的前10持仓集中度阈值
        top10_ratio = etf_holding.top10_ratio
        if top10_ratio > self.config.risk_top10_ratio_high:
            if risk_level == "低":
                risk_level = "中"

        return confidence, risk_level


class SignalEvaluatorFactory:
    """
    信号评估器工厂（使用插件注册表）
    """

    @staticmethod
    def create(evaluator_type: str = "default", config: SignalEvaluationConfig = None) -> SignalEvaluator:
        """
        创建信号评估器

        Args:
            evaluator_type: 评估器类型
            config: 信号评估配置

        Returns:
            SignalEvaluator: 评估器实例

        Raises:
            ValueError: 如果指定的评估器类型未注册
        """
        if config is None:
            config = SignalEvaluationConfig()

        evaluator_cls = evaluator_registry.get(evaluator_type.lower())

        if evaluator_cls is None:
            available = ", ".join(evaluator_registry.list_names())
            raise ValueError(
                f"未知的评估器类型: '{evaluator_type}'. "
                f"可用的类型: {available}"
            )

        return evaluator_cls(config)

    @staticmethod
    def list_available() -> list:
        """
        列出所有可用的评估器类型

        Returns:
            评估器类型名称列表
        """
        return evaluator_registry.list_names()

    @staticmethod
    def register_custom(name: str, cls: Type['SignalEvaluator']) -> None:
        """
        注册自定义评估器（便捷方法）

        Args:
            name: 评估器名称
            cls: 评估器类
        """
        evaluator_registry.register_manual(name, cls)