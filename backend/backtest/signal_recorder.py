"""
信号记录器

记录回测期间触发的所有信号，不模拟实际交易。
"""

from typing import List, Dict, Optional
from datetime import datetime
from collections import Counter
from loguru import logger

from backend.domain.value_objects import TradingSignal
from backend.backtest.metrics import StatisticsCalculator, SignalStatistics


class SignalRecorder:
    """
    信号记录器

    记录回测期间触发的所有信号，用于后续统计分析。
    不模拟实际交易执行，仅记录信号触发情况。
    """

    def __init__(self):
        """初始化信号记录器"""
        self.signals: List[TradingSignal] = []
        self._signal_count_by_date: Dict[str, int] = {}
        self._signal_count_by_stock: Dict[str, int] = {}
        self._signal_count_by_etf: Dict[str, int] = {}
        self._processed_keys: set = set()  # 用于去重

    def record(
        self,
        signals: List[TradingSignal],
        timestamp: datetime,
        dedup: bool = True
    ) -> None:
        """
        记录信号

        Args:
            signals: 信号列表
            timestamp: 时间戳
            dedup: 是否去重（同一天同一股票只记录一次）
        """
        date_str = timestamp.strftime("%Y-%m-%d")

        for signal in signals:
            # 去重检查
            if dedup:
                dedup_key = f"{signal.stock_code}_{date_str}"
                if dedup_key in self._processed_keys:
                    logger.debug(f"信号已记录，跳过: {signal.stock_code} @ {date_str}")
                    continue
                self._processed_keys.add(dedup_key)

            # 记录信号
            self.signals.append(signal)

            # 统计
            self._signal_count_by_date[date_str] = \
                self._signal_count_by_date.get(date_str, 0) + 1

            stock_key = f"{signal.stock_code} {signal.stock_name}"
            self._signal_count_by_stock[stock_key] = \
                self._signal_count_by_stock.get(stock_key, 0) + 1

            etf_key = f"{signal.etf_code} {signal.etf_name}"
            self._signal_count_by_etf[etf_key] = \
                self._signal_count_by_etf.get(etf_key, 0) + 1

            logger.info(
                f"📊 记录信号 #{len(self.signals)}: "
                f"{signal.stock_name} -> {signal.etf_name} "
                f"@ {signal.timestamp}"
            )

    def get_signals(self) -> List[TradingSignal]:
        """获取所有记录的信号"""
        return self.signals.copy()

    def get_signals_by_date(self, date: str) -> List[TradingSignal]:
        """
        获取指定日期的信号

        Args:
            date: 日期字符串 "YYYY-MM-DD"

        Returns:
            该日期的信号列表
        """
        result = []
        for signal in self.signals:
            try:
                signal_date = datetime.strptime(signal.timestamp, "%Y-%m-%d %H:%M:%S")
                if signal_date.strftime("%Y-%m-%d") == date:
                    result.append(signal)
            except ValueError:
                continue
        return result

    def get_signals_by_stock(self, stock_code: str) -> List[TradingSignal]:
        """
        获取指定股票的信号

        Args:
            stock_code: 股票代码

        Returns:
            该股票的信号列表
        """
        return [s for s in self.signals if s.stock_code == stock_code]

    def get_signals_by_etf(self, etf_code: str) -> List[TradingSignal]:
        """
        获取指定ETF的信号

        Args:
            etf_code: ETF代码

        Returns:
            该ETF的信号列表
        """
        return [s for s in self.signals if s.etf_code == etf_code]

    def get_signal_count(self) -> int:
        """获取信号总数"""
        return len(self.signals)

    def get_statistics(self) -> SignalStatistics:
        """
        计算并返回信号统计

        Returns:
            信号统计对象
        """
        return StatisticsCalculator.calculate(self.signals)

    def clear(self) -> None:
        """清空记录"""
        self.signals.clear()
        self._signal_count_by_date.clear()
        self._signal_count_by_stock.clear()
        self._signal_count_by_etf.clear()
        self._processed_keys.clear()
        logger.info("信号记录器已清空")

    def get_summary(self) -> str:
        """获取摘要信息"""
        if not self.signals:
            return "暂无信号记录"

        stats = self.get_statistics()
        lines = [
            "=" * 60,
            "信号记录摘要",
            "=" * 60,
            f"总信号数: {len(self.signals)}",
            f"信号日期数: {len(self._signal_count_by_date)}天",
            f"涉及股票数: {len(self._signal_count_by_stock)}只",
            f"涉及ETF数: {len(self._signal_count_by_etf)}只",
            "",
            "信号最多的股票 (前5):",
        ]

        for stock, count in Counter(self._signal_count_by_stock).most_common(5):
            lines.append(f"  {stock}: {count}次")

        lines.extend([
            "",
            "信号最多的ETF (前5):",
        ])

        for etf, count in Counter(self._signal_count_by_etf).most_common(5):
            lines.append(f"  {etf}: {count}次")

        lines.extend([
            "",
            "按日期统计 (信号最多的5天):",
        ])

        for date, count in Counter(self._signal_count_by_date).most_common(5):
            lines.append(f"  {date}: {count}次")

        lines.append("=" * 60)

        return "\n".join(lines)

    def export_to_dict(self) -> List[Dict]:
        """导出为字典列表"""
        return [signal.to_dict() for signal in self.signals]

    def get_daily_signal_count(self) -> Dict[str, int]:
        """获取每日信号数量"""
        return self._signal_count_by_date.copy()

    def get_stock_signal_count(self) -> Dict[str, int]:
        """获取每只股票的信号数量"""
        return self._signal_count_by_stock.copy()

    def get_etf_signal_count(self) -> Dict[str, int]:
        """获取每个ETF的信号数量"""
        return self._signal_count_by_etf.copy()
