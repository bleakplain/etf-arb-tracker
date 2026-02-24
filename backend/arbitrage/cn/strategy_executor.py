"""
策略执行器 - 负责执行完整的套利策略流程

职责：
1. 协调事件检测、基金选择、信号生成
2. 应用信号过滤策略
3. 评估信号质量
"""

from typing import TYPE_CHECKING, List, Tuple, Optional
from loguru import logger
from datetime import datetime
from dataclasses import replace
import threading
from itertools import count

from backend.arbitrage.models import TradingSignal
from backend.market import CandidateETF
from backend.market.interfaces import IQuoteFetcher
from backend.arbitrage.cn.strategies.interfaces import (
    IEventDetector,
    IFundSelector,
    ISignalFilter,
)
from backend.market.events import MarketEvent

# 延迟导入以避免循环依赖
if TYPE_CHECKING:
    from backend.signal.interfaces import ISignalEvaluator

# 全局信号计数器（线程安全 - itertools.count 原子操作）
_signal_counter = count()


def _generate_signal_id(stock_code: str) -> str:
    """生成唯一信号ID"""
    counter = next(_signal_counter)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"SIG_{timestamp}_{counter:04d}_{stock_code}"


class StrategyExecutor:
    """
    策略执行器

    负责执行完整的套利策略流程，从事件检测到信号生成。
    """

    def __init__(
        self,
        event_detector: IEventDetector,
        fund_selector: IFundSelector,
        signal_filters: list[ISignalFilter],
        etf_quote_provider: IQuoteFetcher,
        signal_evaluator: 'ISignalEvaluator' = None
    ):
        """
        初始化策略执行器

        Args:
            event_detector: 事件检测器
            fund_selector: 基金选择器
            signal_filters: 信号过滤器列表
            etf_quote_provider: ETF行情提供者
            signal_evaluator: 信号评估器（可选）
        """
        self._event_detector = event_detector
        self._fund_selector = fund_selector
        self._signal_filters = signal_filters
        self._etf_quote_provider = etf_quote_provider
        self._signal_evaluator = signal_evaluator

    def execute(
        self,
        quote: dict,
        eligible_funds: list[CandidateETF]
    ) -> tuple[TradingSignal | None, list[str]]:
        """
        执行完整策略流程

        Args:
            quote: 证券行情数据
            eligible_funds: 符合条件的候选ETF列表

        Returns:
            (signal, logs) - (交易信号或None, 执行日志列表)
        """
        logs = []

        # 步骤1: 事件检测
        event = self._detect_event(quote, logs)
        if not event:
            return None, logs

        # 步骤2: 基金选择
        selected_fund = self._select_fund(eligible_funds, event, logs)
        if not selected_fund:
            return None, logs

        # 步骤3: 获取ETF行情
        etf_quote = self._get_etf_quote(selected_fund, logs)
        if not etf_quote:
            return None, logs

        # 步骤4: 生成信号
        signal = self._generate_signal(event, selected_fund, etf_quote, logs)
        if not signal:
            return None, logs

        # 步骤5: 信号过滤
        if not self._apply_signal_filters(event, selected_fund, signal, logs):
            return None, logs

        # 步骤6: 评估信号质量
        signal = self._evaluate_signal(event, selected_fund, signal, logs)

        return signal, logs

    def _detect_event(self, quote: dict, logs: list[str]) -> MarketEvent | None:
        """检测市场事件"""
        event = self._event_detector.detect(quote)
        if not event:
            logs.append(f"未检测到事件: {self._event_detector.strategy_name}")
            return None

        if not self._event_detector.is_valid(event):
            logs.append(f"事件验证失败: {event.event_type}")
            return None

        logs.append(f"✓ 检测到事件: {event.event_type} - {event.stock_name}")
        logs.append(f"  涨幅: +{event.change_pct*100:.2f}%, 价格: ¥{event.price:.2f}")

        return event

    def _select_fund(
        self,
        eligible_funds: list[CandidateETF],
        event: MarketEvent,
        logs: list[str]
    ) -> CandidateETF | None:
        """选择最优基金"""
        if not eligible_funds:
            logs.append("无符合条件的候选基金")
            return None

        selected_fund = self._fund_selector.select(eligible_funds, event)
        if not selected_fund:
            logs.append(f"无符合条件的基金: {len(eligible_funds)}个候选")
            return None

        reason = self._fund_selector.get_selection_reason(selected_fund)
        logs.append(f"✓ 选择基金: {selected_fund.etf_name}")
        logs.append(f"  理由: {reason}")

        return selected_fund

    def _get_etf_quote(
        self,
        selected_fund: CandidateETF,
        logs: list[str]
    ) -> dict | None:
        """获取ETF行情"""
        etf_quote = self._etf_quote_provider.get_etf_quote(selected_fund.etf_code)
        if not etf_quote:
            logs.append(f"无法获取基金行情: {selected_fund.etf_code}")
            return None

        return etf_quote

    def _generate_signal(
        self,
        event: MarketEvent,
        selected_fund: CandidateETF,
        etf_quote: dict,
        logs: list[str]
    ) -> TradingSignal | None:
        """生成交易信号"""
        return TradingSignal(
            signal_id=_generate_signal_id(event.stock_code),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            stock_code=event.stock_code,
            stock_name=event.stock_name,
            stock_price=event.price,
            limit_time=getattr(event, 'limit_time', ''),
            locked_amount=getattr(event, 'locked_amount', 0),
            change_pct=event.change_pct,
            etf_code=selected_fund.etf_code,
            etf_name=selected_fund.etf_name,
            etf_weight=selected_fund.weight,
            etf_price=etf_quote.get('price', 0.0),
            etf_premium=etf_quote.get('premium', 0.0),
            etf_amount=etf_quote.get('amount', 0.0),
            reason=self._build_reason(event, selected_fund),
            confidence="",
            risk_level="",
            actual_weight=selected_fund.weight,
            weight_rank=selected_fund.rank,
            top10_ratio=selected_fund.top10_ratio
        )

    @staticmethod
    def _build_reason(event: MarketEvent, fund: CandidateETF) -> str:
        """构建信号原因"""
        limit_time = getattr(event, 'limit_time', '')
        change_pct_str = f"涨停 ({event.change_pct*100:.2f}%)" if limit_time else f"{event.event_type} ({event.change_pct*100:.2f}%)"
        return f"{event.stock_name} {change_pct_str}，在 {fund.etf_name} 中持仓占比 {fund.weight_pct:.2f}% (排名第{fund.rank})"

    def _apply_signal_filters(
        self,
        event: MarketEvent,
        selected_fund: CandidateETF,
        signal: TradingSignal,
        logs: List[str]
    ) -> bool:
        """
        应用信号过滤器

        Returns:
            True表示通过所有过滤器，False表示被拒绝
        """
        for filter_strategy in self._signal_filters:
            should_filter, reason = filter_strategy.filter(event, selected_fund, signal)

            if should_filter:
                if filter_strategy.is_required:
                    logs.append(f"✗ 信号被拒绝({filter_strategy.strategy_name}): {reason}")
                    return False
                else:
                    logs.append(f"⚠️  警告({filter_strategy.strategy_name}): {reason}")

        return True

    def _evaluate_signal(
        self,
        event: MarketEvent,
        selected_fund: CandidateETF,
        signal: TradingSignal,
        logs: List[str]
    ) -> TradingSignal:
        """
        评估信号质量

        Returns:
            评估后的信号（使用 dataclasses.replace 创建新实例）
        """
        if not self._signal_evaluator:
            # 默认评估
            confidence = "中"
            risk_level = "中"
        else:
            confidence, risk_level = self._signal_evaluator.evaluate(event, selected_fund)

        logs.append(f"✓ 信号评估: 置信度={confidence}, 风险={risk_level}")

        # 使用 replace 创建新实例（因为 TradingSignal 是 frozen）
        return replace(signal, confidence=confidence, risk_level=risk_level)
