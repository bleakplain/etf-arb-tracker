"""
信号评估器模块
使用策略模式实现不同的信号评估策略

支持插件式扩展：通过装饰器注册新的评估器
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, Type
from datetime import datetime

from config.strategy import SignalEvaluationConfig
from backend.domain.interfaces import ISignalEvaluator
from backend.core.registry import evaluator_registry


class SignalEvaluator(ISignalEvaluator, ABC):
    """
    信号评估器基类（实现接口）

    所有自定义评估器应继承此类并使用 @evaluator_registry.register() 装饰器注册。

    Example:
        @evaluator_registry.register("custom", priority=50, description="My custom evaluator")
        class MyCustomEvaluator(SignalEvaluator):
            def evaluate(self, limit_info: Dict, etf_info: Dict) -> Tuple[str, str]:
                return "高", "低"
    """

    def __init__(self, config: SignalEvaluationConfig):
        self.config = config

    @abstractmethod
    def evaluate(self, limit_info: Dict, etf_info: Dict) -> Tuple[str, str]:
        """
        评估信号质量

        Args:
            limit_info: 涨停股票信息
            etf_info: ETF信息

        Returns:
            (confidence, risk_level) - (置信度, 风险等级)
        """

    @staticmethod
    def _get_time_to_close() -> int:
        """
        获取距离收盘的秒数

        Returns:
            距离15:00收盘的秒数，不在交易时间返回-1
        """
        now = datetime.now()
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

    def evaluate(self, limit_info: Dict, etf_info: Dict) -> Tuple[str, str]:
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
        weight = etf_info.get('weight', 0)
        if weight >= self.config.confidence_high_weight:
            confidence = "高"
        elif weight < self.config.confidence_low_weight:
            confidence = "低"

        # 2. 排名评估
        rank = etf_info.get('rank', -1)
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
        top10_ratio = etf_info.get('top10_ratio', 0)
        if top10_ratio > self.config.risk_top10_ratio_high:
            if risk_level == "低":
                risk_level = "中"
            elif risk_level == "中":
                risk_level = "高"

        # 5. 涨停时间因素
        current_hour = datetime.now().hour
        if current_hour < self.config.risk_morning_hour:
            if risk_level == "高":
                risk_level = "中"

        return confidence, risk_level

    @staticmethod
    def _get_time_to_close() -> int:
        """获取距离收盘的秒数"""
        now = datetime.now()
        close_time = now.replace(hour=15, minute=0, second=0, microsecond=0)

        if now.hour < 9 or now.hour >= 15:
            return -1

        delta = close_time - now
        return int(delta.total_seconds())


class ConservativeEvaluator(SignalEvaluator):
    """
    保守型评估器 - 更严格的评估标准

    注意：此类保留用于向后兼容，建议使用自定义评估器
    """

    def evaluate(self, limit_info: Dict, etf_info: Dict) -> Tuple[str, str]:
        """保守型评估 - 偏向低置信度、高风险"""
        weight = etf_info.get('weight', 0)
        rank = etf_info.get('rank', -1)

        # 更严格的权重要求
        if weight >= 0.15:
            confidence = "高"
        elif weight >= 0.08:
            confidence = "中"
        else:
            confidence = "低"

        # 更严格的排名要求
        if rank > 5:
            confidence = "低"

        # 更保守的时间评估
        time_to_close = SignalEvaluator._get_time_to_close()
        if time_to_close < 1800:  # 30分钟内即为高风险
            risk_level = "高"
        elif time_to_close > 7200:  # 2小时以上才低风险
            risk_level = "低"
        else:
            risk_level = "中"

        # 持仓集中度风险
        top10_ratio = etf_info.get('top10_ratio', 0)
        if top10_ratio > 0.60:  # 前10占比超过60%即高风险
            risk_level = "高"

        return confidence, risk_level


class AggressiveEvaluator(SignalEvaluator):
    """激进型评估器 - 更宽松的评估标准"""

    def evaluate(self, limit_info: Dict, etf_info: Dict) -> Tuple[str, str]:
        """激进型评估 - 偏向高置信度、低风险"""
        weight = etf_info.get('weight', 0)
        rank = etf_info.get('rank', -1)

        # 更宽松的权重要求
        if weight >= 0.08:
            confidence = "高"
        elif weight >= 0.03:
            confidence = "中"
        else:
            confidence = "低"

        # 更宽松的排名要求
        if rank <= 20:
            if confidence == "低":
                confidence = "中"

        # 更激进的时间评估
        time_to_close = SignalEvaluator._get_time_to_close()
        if time_to_close < 300:  # 5分钟内才高风险
            risk_level = "高"
        elif time_to_close > 1800:  # 30分钟以上即低风险
            risk_level = "低"
        else:
            risk_level = "中"

        return confidence, risk_level


class SignalEvaluatorFactory:
    """
    信号评估器工厂（使用插件注册表）

    现在支持通过插件注册表动态获取评估器，
    无需修改此工厂类即可添加新的评估器类型。
    """

    @staticmethod
    def create(evaluator_type: str = "default", config: SignalEvaluationConfig = None) -> SignalEvaluator:
        """
        创建信号评估器

        Args:
            evaluator_type: 评估器类型 ('default', 'conservative', 'aggressive' 或自定义名称)
            config: 信号评估配置

        Returns:
            SignalEvaluator: 评估器实例

        Raises:
            ValueError: 如果指定的评估器类型未注册
        """
        if config is None:
            # 使用默认配置
            config = SignalEvaluationConfig()

        # 从注册表获取评估器类
        evaluator_cls = evaluator_registry.get(evaluator_type.lower())

        if evaluator_cls is None:
            # 尝试不区分大小写查找
            for name in evaluator_registry.list_names():
                if name.lower() == evaluator_type.lower():
                    evaluator_cls = evaluator_registry.get(name)
                    break

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
