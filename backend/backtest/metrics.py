"""
回测统计指标

定义回测结果的数据结构和统计计算。
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any
from datetime import datetime
from collections import Counter

from backend.arbitrage.models import TradingSignal


@dataclass
class SignalStatistics:
    """信号统计指标"""
    total_signals: int = 0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    most_triggered_stocks: List[Tuple[str, int]] = field(default_factory=list)
    most_used_etfs: List[Tuple[str, int]] = field(default_factory=list)
    signals_by_date: Dict[str, int] = field(default_factory=dict)
    signals_by_month: Dict[str, int] = field(default_factory=dict)
    signals_by_stock: Dict[str, int] = field(default_factory=dict)

    def get_confidence_distribution(self) -> Dict[str, float]:
        """获取置信度分布百分比"""
        total = self.total_signals or 1
        return {
            "高": self.high_confidence_count / total * 100,
            "中": self.medium_confidence_count / total * 100,
            "低": self.low_confidence_count / total * 100
        }

    def get_risk_distribution(self) -> Dict[str, float]:
        """获取风险等级分布百分比"""
        total = self.total_signals or 1
        return {
            "高": self.high_risk_count / total * 100,
            "中": self.medium_risk_count / total * 100,
            "低": self.low_risk_count / total * 100
        }

    def get_average_signals_per_day(self) -> float:
        """获取平均每天信号数量"""
        days = len(self.signals_by_date) or 1
        return self.total_signals / days

    def get_average_signals_per_month(self) -> float:
        """获取平均每月信号数量"""
        months = len(self.signals_by_month) or 1
        return self.total_signals / months

    def get_max_signals_day(self) -> Tuple[str, int]:
        """获取信号数量最多的日期"""
        if not self.signals_by_date:
            return ("无", 0)
        return max(self.signals_by_date.items(), key=lambda x: x[1])

    def get_summary(self) -> str:
        """获取统计摘要"""
        lines = [
            "=" * 60,
            "回测统计摘要",
            "=" * 60,
            f"总信号数: {self.total_signals}",
            "",
            "置信度分布:",
            dist := self.get_confidence_distribution(),
            f"  高: {dist['高']:.1f}%",
            f"  中: {dist['中']:.1f}%",
            f"  低: {dist['低']:.1f}%",
            "",
            "风险等级分布:",
            risk := self.get_risk_distribution(),
            f"  高风险: {self.high_risk_count} ({risk['高']:.1f}%)",
            f"  中风险: {self.medium_risk_count} ({risk['中']:.1f}%)",
            f"  低风险: {self.low_risk_count} ({risk['低']:.1f}%)",
            "",
            f"平均每天信号数: {self.get_average_signals_per_day():.1f}",
            f"平均每月信号数: {self.get_average_signals_per_month():.1f}",
            "",
        ]

        if self.most_triggered_stocks:
            lines.extend([
                "最常触发股票 (前5):",
            ])
            for stock, count in self.most_triggered_stocks[:5]:
                lines.append(f"  {stock}: {count}次")
            lines.append("")

        if self.most_used_etfs:
            lines.extend([
                "最常用ETF (前5):",
            ])
            for etf, count in self.most_used_etfs[:5]:
                lines.append(f"  {etf}: {count}次")
            lines.append("")

        max_day, max_count = self.get_max_signals_day()
        lines.extend([
            f"信号最多日期: {max_day} ({max_count}个)",
            "=" * 60
        ])

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_signals": self.total_signals,
            "high_confidence_count": self.high_confidence_count,
            "medium_confidence_count": self.medium_confidence_count,
            "low_confidence_count": self.low_confidence_count,
            "high_risk_count": self.high_risk_count,
            "medium_risk_count": self.medium_risk_count,
            "low_risk_count": self.low_risk_count,
            "confidence_distribution": self.get_confidence_distribution(),
            "risk_distribution": self.get_risk_distribution(),
            "average_signals_per_day": self.get_average_signals_per_day(),
            "average_signals_per_month": self.get_average_signals_per_month(),
            "most_triggered_stocks": self.most_triggered_stocks,
            "most_used_etfs": self.most_used_etfs,
            "signals_by_date": self.signals_by_date,
            "signals_by_month": self.signals_by_month,
        }


@dataclass
class BacktestResult:
    """
    回测结果

    包含所有信号和统计信息
    """
    signals: List[TradingSignal]
    statistics: SignalStatistics
    date_range: Tuple[str, str]
    time_granularity: str
    parameters: Dict[str, Any]
    data_details: Dict[str, Any] = field(default_factory=dict)

    @property
    def start_date(self) -> str:
        """开始日期"""
        return self.date_range[0]

    @property
    def end_date(self) -> str:
        """结束日期"""
        return self.date_range[1]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "date_range": {
                "start": self.start_date,
                "end": self.end_date
            },
            "time_granularity": self.time_granularity,
            "parameters": self.parameters,
            "statistics": self.statistics.to_dict(),
            "signals": [signal.to_dict() for signal in self.signals],
            "data_details": self.data_details
        }


class StatisticsCalculator:
    """统计计算器"""

    @staticmethod
    def calculate(signals: List[TradingSignal]) -> SignalStatistics:
        """
        计算信号统计

        Args:
            signals: 信号列表

        Returns:
            统计结果
        """
        stats = SignalStatistics(total_signals=len(signals))

        if not signals:
            return stats

        # 按置信度分组
        confidence_counter = Counter(s.confidence for s in signals)
        stats.high_confidence_count = confidence_counter.get("高", 0)
        stats.medium_confidence_count = confidence_counter.get("中", 0)
        stats.low_confidence_count = confidence_counter.get("低", 0)

        # 按风险等级分组
        risk_counter = Counter(s.risk_level for s in signals)
        stats.high_risk_count = risk_counter.get("高", 0)
        stats.medium_risk_count = risk_counter.get("中", 0)
        stats.low_risk_count = risk_counter.get("低", 0)

        # 按日期分组
        date_counter = Counter()
        month_counter = Counter()
        for signal in signals:
            try:
                dt = datetime.strptime(signal.timestamp, "%Y-%m-%d %H:%M:%S")
                date_str = dt.strftime("%Y-%m-%d")
                month_str = dt.strftime("%Y-%m")
                date_counter[date_str] += 1
                month_counter[month_str] += 1
            except ValueError:
                continue

        stats.signals_by_date = dict(date_counter)
        stats.signals_by_month = dict(month_counter)

        # 按股票分组
        stock_counter = Counter(
            f"{signal.stock_code} {signal.stock_name}"
            for signal in signals
        )
        stats.most_triggered_stocks = stock_counter.most_common(10)
        stats.signals_by_stock = dict(stock_counter)

        # 按ETF分组
        etf_counter = Counter(
            f"{signal.etf_code} {signal.etf_name}"
            for signal in signals
        )
        stats.most_used_etfs = etf_counter.most_common(10)

        return stats
