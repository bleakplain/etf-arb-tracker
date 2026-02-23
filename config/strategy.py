"""
策略配置模块

定义交易策略的参数设置
"""

from dataclasses import dataclass
from typing import List


@dataclass
class TradingHours:
    """交易时间设置"""

    morning_start: str = "09:30"
    morning_end: str = "11:30"
    afternoon_start: str = "13:00"
    afternoon_end: str = "15:00"

    @classmethod
    def from_dict(cls, data: dict) -> "TradingHours":
        """从字典创建配置"""
        morning = data.get("morning", {})
        afternoon = data.get("afternoon", {})
        return cls(
            morning_start=morning.get("start", "09:30"),
            morning_end=morning.get("end", "11:30"),
            afternoon_start=afternoon.get("start", "13:00"),
            afternoon_end=afternoon.get("end", "15:00"),
        )


@dataclass
class StrategySettings:
    """策略设置"""

    # 扫描间隔（秒）
    scan_interval: int = 120

    # ETF持仓权重阈值
    min_weight: float = 0.05

    # 最小封单量（亿元）
    min_order_amount: float = 10.0

    # 距收盘最小时间（秒）
    min_time_to_close: int = 1800

    # ETF最小日成交额（万元）
    min_etf_volume: float = 5000.0

    # 最大持仓数量
    max_positions: int = 5

    @classmethod
    def from_dict(cls, data: dict) -> "StrategySettings":
        """从字典创建配置"""
        return cls(
            scan_interval=data.get("scan_interval", 120),
            min_weight=data.get("min_weight", 0.05),
            min_order_amount=data.get("min_order_amount", 10.0),
            min_time_to_close=data.get("min_time_to_close", 1800),
            min_etf_volume=data.get("min_etf_volume", 5000.0),
            max_positions=data.get("max_positions", 5),
        )


@dataclass
class RiskControlSettings:
    """风控设置"""

    # 单次最大买入金额（万元）
    max_buy_amount: float = 50.0

    # 止盈点（%）
    take_profit: float = 3.0

    # 止损点（%）
    stop_loss: float = -2.0

    # 持仓天数上限
    max_hold_days: int = 3

    @classmethod
    def from_dict(cls, data: dict) -> "RiskControlSettings":
        """从字典创建配置"""
        return cls(
            max_buy_amount=data.get("max_buy_amount", 50.0),
            take_profit=data.get("take_profit", 3.0),
            stop_loss=data.get("stop_loss", -2.0),
            max_hold_days=data.get("max_hold_days", 3),
        )


@dataclass
class SignalEvaluationConfig:
    """信号评估配置 - 默认值"""

    # 置信度评估 - 权重阈值
    confidence_high_weight: float = 0.10      # 权重>=10%为高置信度
    confidence_low_weight: float = 0.05       # 权重<5%为低置信度

    # 置信度评估 - 排名阈值
    confidence_high_rank: int = 3             # 排名<=3为高置信度
    confidence_low_rank: int = 10             # 排名>10为低置信度

    # 风险评估 - 时间阈值（秒）
    risk_high_time_seconds: int = 600         # 距收盘<10分钟为高风险
    risk_low_time_seconds: int = 3600         # 距收盘>1小时为低风险

    # 风险评估 - 持仓集中度阈值
    risk_top10_ratio_high: float = 0.70       # 前10占比>70%为高风险

    # 风险评估 - 时间因素（小时）
    risk_morning_hour: int = 10               # 10点前涨停风险降低

    @classmethod
    def from_dict(cls, data: dict) -> "SignalEvaluationConfig":
        """从字典创建配置"""
        return cls(
            confidence_high_weight=data.get("confidence_high_weight", 0.10),
            confidence_low_weight=data.get("confidence_low_weight", 0.05),
            confidence_high_rank=data.get("confidence_high_rank", 3),
            confidence_low_rank=data.get("confidence_low_rank", 10),
            risk_high_time_seconds=data.get("risk_high_time_seconds", 600),
            risk_low_time_seconds=data.get("risk_low_time_seconds", 3600),
            risk_top10_ratio_high=data.get("risk_top10_ratio_high", 0.70),
            risk_morning_hour=data.get("risk_morning_hour", 10),
        )


@dataclass
class ConservativeEvaluationConfig(SignalEvaluationConfig):
    """保守型评估配置 - 更严格的阈值"""

    # 更严格的权重要求（覆盖默认值）
    confidence_high_weight: float = 0.15      # 15%以上才高置信度
    confidence_medium_weight: float = 0.08     # 8%以上为中等置信度
    confidence_low_weight: float = 0.05        # 5%以下为低置信度

    # 更严格的排名要求
    confidence_high_rank: int = 3              # 排名<=3为高置信度
    confidence_strict_rank: int = 5            # 排名>5即降为低置信度

    # 更保守的时间评估
    risk_high_time_seconds: int = 1800         # 30分钟内即高风险
    risk_low_time_seconds: int = 7200          # 2小时以上才低风险

    # 更严格的前10持仓集中度要求
    risk_top10_ratio_high: float = 0.60        # 前10占比>60%即高风险


@dataclass
class AggressiveEvaluationConfig(SignalEvaluationConfig):
    """激进型评估配置 - 更宽松的阈值"""

    # 更宽松的权重要求（覆盖默认值）
    confidence_high_weight: float = 0.08      # 8%以上即为高置信度
    confidence_medium_weight: float = 0.03     # 3%以上为中等置信度
    confidence_low_weight: float = 0.01        # 1%以下才低置信度

    # 更宽松的排名要求
    confidence_high_rank: int = 5              # 排名<=5为高置信度
    confidence_low_rank: int = 15              # 排名>15才低置信度

    # 更宽松的时间评估
    risk_high_time_seconds: int = 300          # 5分钟内才高风险
    risk_low_time_seconds: int = 1800          # 30分钟以上即低风险

    # 更宽松的持仓集中度要求
    risk_top10_ratio_high: float = 0.80        # 前10占比>80%才高风险

