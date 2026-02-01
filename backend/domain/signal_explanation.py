"""
信号解释值对象

用于向用户解释为什么产生某个交易信号
"""

from dataclasses import dataclass
from typing import List, Literal, Optional


@dataclass
class ScoreItem:
    """评分项"""
    name: str  # 评分项名称
    score: int  # 分数 0-100
    weight: float  # 权重
    value: float  # 原始值
    threshold: float  # 阈值
    passed: bool  # 是否通过

    @property
    def weighted_score(self) -> float:
        """加权分数"""
        return self.score * self.weight


@dataclass
class ConfidenceBreakdown:
    """置信度评分拆解"""
    total_score: int  # 总分 0-100
    level: Literal["high", "medium", "low"]  # 置信度等级
    order_amount_score: ScoreItem  # 封单量评分
    weight_score: ScoreItem  # 权重评分
    liquidity_score: ScoreItem  # 流动性评分
    time_to_close_score: ScoreItem  # 距收盘评分

    def scores(self) -> List[ScoreItem]:
        """获取所有评分项"""
        return [
            self.order_amount_score,
            self.weight_score,
            self.liquidity_score,
            self.time_to_close_score
        ]

    @classmethod
    def from_signal(
        cls,
        seal_amount: float,
        weight: float,
        etf_volume: float,
        time_to_close: int,
        thresholds: dict
    ) -> "ConfidenceBreakdown":
        """从信号数据创建置信度拆解

        Args:
            seal_amount: 封单量（亿元）
            weight: ETF持仓权重
            etf_volume: ETF成交额（万元）
            time_to_close: 距收盘秒数
            thresholds: 各项阈值配置
        """
        # 封单量评分 (0-30分)
        min_seal = thresholds.get("min_order_amount", 10)
        seal_score = min(100, int((seal_amount / min_seal) * 80))
        order_item = ScoreItem(
            name="封单量评分",
            score=seal_score,
            weight=0.30,
            value=seal_amount,
            threshold=min_seal,
            passed=seal_amount >= min_seal
        )

        # 权重评分 (0-30分)
        min_weight = thresholds.get("min_weight", 0.05)
        weight_score = min(100, int((weight / min_weight) * 80))
        weight_item = ScoreItem(
            name="权重评分",
            score=weight_score,
            weight=0.30,
            value=weight,
            threshold=min_weight,
            passed=weight >= min_weight
        )

        # 流动性评分 (0-25分)
        min_volume = thresholds.get("min_etf_volume", 5000)
        volume_score = min(100, int((etf_volume / min_volume) * 80))
        liquidity_item = ScoreItem(
            name="流动性评分",
            score=volume_score,
            weight=0.25,
            value=etf_volume,
            threshold=min_volume,
            passed=etf_volume >= min_volume
        )

        # 距收盘评分 (0-15分)
        min_time = thresholds.get("min_time_to_close", 1800)
        # 时间越长越好，最高1800秒=30分钟
        time_score = min(100, int((time_to_close / min_time) * 80))
        time_item = ScoreItem(
            name="距收盘评分",
            score=time_score,
            weight=0.15,
            value=time_to_close,
            threshold=min_time,
            passed=time_to_close >= min_time
        )

        # 计算总分
        total = int(sum(item.weighted_score for item in [
            order_item, weight_item, liquidity_item, time_item
        ]))

        # 确定等级
        if total >= 80:
            level = "high"
        elif total >= 60:
            level = "medium"
        else:
            level = "low"

        return cls(
            total_score=total,
            level=level,
            order_amount_score=order_item,
            weight_score=weight_item,
            liquidity_score=liquidity_item,
            time_to_close_score=time_item
        )


@dataclass
class SignalReason:
    """信号产生原因"""
    stock_code: str
    stock_name: str
    limit_up_price: float
    seal_amount: float  # 亿元
    time_to_close: int  # 秒
    etf_code: str
    etf_name: str
    etf_weight: float
    etf_volume: float  # 万元
    all_checks_passed: List[str]  # 所有通过的检查项
    warnings: List[str]  # 警告信息

    @classmethod
    def from_signal_data(
        cls,
        stock_code: str,
        stock_name: str,
        limit_price: float,
        seal: float,
        time_to_close: int,
        etf_code: str,
        etf_name: str,
        weight: float,
        volume: float,
        thresholds: dict
    ) -> "SignalReason":
        """从信号数据创建原因说明"""
        checks = []
        warnings = []

        # 股票涨停检查
        checks.append(f"{stock_name} ({stock_code}) 涨停，价格 ¥{limit_price:.2f}")

        # 封单量检查
        min_seal = thresholds.get("min_order_amount", 10)
        if seal >= min_seal:
            checks.append(f"封单量 ¥{seal:.1f}亿 ≥ {min_seal}亿阈值")
        else:
            warnings.append(f"封单量 ¥{seal:.1f}亿 低于 {min_seal}亿阈值")

        # ETF持仓检查
        min_weight = thresholds.get("min_weight", 0.05)
        weight_pct = weight * 100
        if weight >= min_weight:
            checks.append(f"ETF {etf_name} 持有 {weight_pct:.1f}% ≥ {min_weight*100:.0f}%阈值")
        else:
            warnings.append(f"ETF持仓 {weight_pct:.1f}% 低于 {min_weight*100:.0f}%阈值")

        # 流动性检查
        min_volume = thresholds.get("min_etf_volume", 5000)
        if volume >= min_volume:
            checks.append(f"ETF成交额 ¥{volume:.0f}万 ≥ {min_volume}万阈值")
        else:
            warnings.append(f"ETF成交额 ¥{volume:.0f}万 低于 {min_volume}万阈值")

        # 距收盘检查
        min_time = thresholds.get("min_time_to_close", 1800)
        time_minutes = time_to_close / 60
        if time_to_close >= min_time:
            checks.append(f"距收盘 {time_minutes:.0f}分钟 ≥ {min_time/60:.0f}分钟阈值")
        else:
            warnings.append(f"距收盘仅 {time_minutes:.0f}分钟，建议谨慎")

        return cls(
            stock_code=stock_code,
            stock_name=stock_name,
            limit_up_price=limit_price,
            seal_amount=seal,
            time_to_close=time_to_close,
            etf_code=etf_code,
            etf_name=etf_name,
            etf_weight=weight,
            etf_volume=volume,
            all_checks_passed=checks,
            warnings=warnings
        )


@dataclass
class DataSourceInfo:
    """数据来源信息"""
    stock_data_source: str  # 股票数据来源
    stock_data_complete: bool  # 股票数据是否完整
    etf_data_source: str  # ETF数据来源
    etf_data_complete: bool  # ETF数据是否完整
    holdings_data_source: str  # 持仓数据来源
    holdings_interpolation: str  # 持仓插值方式


@dataclass
class SignalDetailResponse:
    """信号详情响应"""
    signal_id: str
    timestamp: str
    reason: SignalReason
    confidence: ConfidenceBreakdown
    data_source: DataSourceInfo
