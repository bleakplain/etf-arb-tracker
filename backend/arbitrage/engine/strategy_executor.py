"""
策略执行器 - 负责执行策略链

策略链流程：
1. EventDetector (事件检测)
   ↓
2. FundSelector (基金选择)
   ↓
3. SignalFilters (信号过滤，可多个)
   ↓
4. TradingSignal (最终信号)
"""

from typing import List, Optional, Dict, Any
from loguru import logger

from backend.arbitrage.domain.interfaces import (
    IEventDetectorStrategy,
    IFundSelectionStrategy,
    ISignalFilterStrategy,
    EventInfo,
    CandidateETF,
    TradingSignal
)


class StrategyExecutor:
    """
    策略执行器

    负责按照策略链的顺序执行各个策略组件，
    最终生成交易信号或返回失败原因。
    """

    def __init__(
        self,
        event_detector: IEventDetectorStrategy,
        fund_selector: IFundSelectionStrategy,
        signal_filters: List[ISignalFilterStrategy] = None
    ):
        """
        初始化策略执行器

        Args:
            event_detector: 事件检测策略
            fund_selector: 基金选择策略
            signal_filters: 信号过滤策略列表
        """
        self._event_detector = event_detector
        self._fund_selector = fund_selector
        self._signal_filters = signal_filters or []

        # 记录策略信息
        self._strategy_info = {
            'event_detector': event_detector.strategy_name,
            'fund_selector': fund_selector.strategy_name,
            'signal_filters': [f.filter_name for f in self._signal_filters]
        }

    @property
    def strategy_info(self) -> Dict[str, Any]:
        """获取当前策略信息"""
        return self._strategy_info.copy()

    def execute(
        self,
        quote: Dict,
        eligible_funds: List[CandidateETF],
        etf_quote_provider,
        signal_evaluator
    ) -> tuple[Optional[TradingSignal], List[str]]:
        """
        执行策略链

        Args:
            quote: 证券行情数据
            eligible_funds: 符合条件的基金列表
            etf_quote_provider: ETF行情提供者（用于获取实时数据）
            signal_evaluator: 信号评估器（用于评估信号质量）

        Returns:
            (signal, logs) - (交易信号或None, 执行日志列表)
        """
        logs = []

        # 步骤1: 事件检测
        event = self._event_detector.detect(quote)
        if not event:
            return None, [f"未检测到事件: {self._event_detector.strategy_name}"]

        if not self._event_detector.is_valid(event):
            return None, [f"事件验证失败: {event.event_type}"]

        logs.append(f"✓ 检测到事件: {event.event_type} - {event.security_name}")
        logs.append(f"  涨幅: +{event.change_pct*100:.2f}%, 价格: ¥{event.price:.2f}")

        # 步骤2: 基金选择
        selected_fund = self._fund_selector.select(eligible_funds, event)
        if not selected_fund:
            return None, [f"无符合条件的基金: {len(eligible_funds)}个候选"]

        reason = self._fund_selector.get_selection_reason(selected_fund)
        logs.append(f"✓ 选择基金: {selected_fund.etf_name}")
        logs.append(f"  理由: {reason}")

        # 步骤3: 获取ETF行情
        etf_quote = etf_quote_provider.get_etf_quote(selected_fund.etf_code)
        if not etf_quote:
            return None, [f"无法获取基金行情: {selected_fund.etf_code}"]

        # 步骤4: 生成初步信号
        from datetime import datetime

        signal = TradingSignal(
            signal_id=f"SIG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{event.security_code}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            stock_code=event.security_code,
            stock_name=event.security_name,
            stock_price=event.price,
            limit_time=event.trigger_time,
            seal_amount=event.metadata.get('seal_amount', 0),
            change_pct=event.change_pct,
            etf_code=selected_fund.etf_code,
            etf_name=selected_fund.etf_name,
            etf_weight=selected_fund.weight,
            etf_price=etf_quote.get('price', 0.0),
            etf_premium=etf_quote.get('premium', 0.0),
            reason=f"{event.security_name} {event.event_type} ({event.change_pct*100:.2f}%)，"
                   f"在 {selected_fund.etf_name} 中持仓占比 {selected_fund.weight_pct:.2f}% "
                   f"(排名第{selected_fund.rank})",
            confidence="",
            risk_level="",
            actual_weight=selected_fund.weight,
            weight_rank=selected_fund.rank,
            top10_ratio=selected_fund.top10_ratio
        )

        # 步骤5: 信号过滤
        for filter_strategy in self._signal_filters:
            should_filter, reason = filter_strategy.should_filter(event, selected_fund, signal)

            if should_filter:
                is_required = filter_strategy.is_required()
                if is_required:
                    return None, [f"信号被拒绝({filter_strategy.filter_name}): {reason}"]
                else:
                    logs.append(f"⚠️  警告({filter_strategy.filter_name}): {reason}")

        # 步骤6: 评估信号质量
        if signal_evaluator:
            etf_info = {
                'weight': selected_fund.weight,
                'rank': selected_fund.rank,
                'in_top10': selected_fund.in_top10,
                'top10_ratio': selected_fund.top10_ratio
            }
            event_dict = event.to_dict()
            confidence, risk_level = signal_evaluator.evaluate(event_dict, etf_info)

            # 更新信号
            signal.confidence = confidence
            signal.risk_level = risk_level

            logs.append(f"✓ 信号评估: 置信度={confidence}, 风险={risk_level}")

        logs.append(f"✓ 信号生成完成: {signal.stock_name} → {signal.etf_name}")
        return signal, logs

    def validate(self) -> tuple[bool, List[str]]:
        """
        验证策略链配置是否有效

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        if not self._event_detector:
            errors.append("缺少事件检测策略")

        if not self._fund_selector:
            errors.append("缺少基金选择策略")

        if not self._signal_filters:
            errors.append("缺少信号过滤策略（建议至少添加时间过滤）")

        return len(errors) == 0, errors
