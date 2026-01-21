"""
信号生成器 - 专职生成交易信号
"""

from typing import Optional, List
from datetime import datetime
from loguru import logger

from backend.domain.interfaces import (
    IQuoteFetcher,
    IETFQuoteProvider,
    ISignalEvaluator
)
from backend.domain.models import LimitUpInfo
from backend.domain.value_objects import ETFReference, TradingSignal


class SignalGenerator:
    """
    信号生成器

    职责：
    1. 根据涨停信息选择最佳ETF
    2. 验证时间、流动性等条件
    3. 评估信号质量
    4. 生成交易信号
    """

    def __init__(
        self,
        quote_fetcher: IQuoteFetcher,
        etf_quote_provider: IETFQuoteProvider,
        signal_evaluator: ISignalEvaluator,
        min_time_to_close: int = 1800,
        min_etf_volume: float = 50000000  # 5000万元
    ):
        """
        初始化信号生成器

        Args:
            quote_fetcher: 行情数据获取器
            etf_quote_provider: ETF行情提供者
            signal_evaluator: 信号评估器
            min_time_to_close: 距收盘最小时间（秒）
            min_etf_volume: ETF最小日成交额
        """
        self._quote_fetcher = quote_fetcher
        self._etf_quote_provider = etf_quote_provider
        self._signal_evaluator = signal_evaluator
        self._min_time_to_close = min_time_to_close
        self._min_etf_volume = min_etf_volume

    def generate_signal(
        self,
        limit_info: LimitUpInfo,
        eligible_etfs: List[ETFReference]
    ) -> Optional[TradingSignal]:
        """
        生成交易信号

        Args:
            limit_info: 涨停信息
            eligible_etfs: 符合条件的ETF列表

        Returns:
            交易信号，不符合条件返回None
        """
        if not eligible_etfs:
            logger.info(
                f"⚠️  {limit_info.stock_code} {limit_info.stock_name} 涨停，"
                f"但无符合条件的ETF"
            )
            return None

        # 选择权重最高的ETF
        best_etf = eligible_etfs[0]
        logger.info(
            f"✓ 选择 {best_etf.etf_name}，权重 {best_etf.weight_pct:.2f}%，"
            f"排名第{best_etf.rank}"
        )

        # 获取ETF行情
        etf_quote = self._etf_quote_provider.get_etf_quote(best_etf.etf_code)
        if not etf_quote:
            logger.warning(f"无法获取 {best_etf.etf_name} 行情")
            return None

        # 检查时间限制
        time_to_close = self._quote_fetcher.get_time_to_close()
        if 0 < time_to_close < self._min_time_to_close:
            logger.info(f"⚠️  距收盘仅{time_to_close//60}分钟，时间不足，跳过")
            return None

        # 检查ETF流动性
        if not self._etf_quote_provider.check_liquidity(
            best_etf.etf_code, self._min_etf_volume
        ):
            logger.info(f"⚠️  {best_etf.etf_name} 流动性不足，跳过")
            return None

        # 评估信号质量
        etf_info = {
            'weight': best_etf.weight,
            'rank': best_etf.rank,
            'in_top10': best_etf.in_top10,
            'top10_ratio': best_etf.top10_ratio
        }
        limit_dict = limit_info.to_dict()
        confidence, risk_level = self._signal_evaluator.evaluate(limit_dict, etf_info)

        # 生成信号
        signal = TradingSignal(
            signal_id=f"SIG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{limit_info.stock_code}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            stock_code=limit_info.stock_code,
            stock_name=limit_info.stock_name,
            stock_price=limit_info.price,
            limit_time=limit_info.limit_time,
            seal_amount=limit_info.seal_amount,
            change_pct=limit_info.change_pct,
            etf_code=best_etf.etf_code,
            etf_name=best_etf.etf_name,
            etf_weight=best_etf.weight,
            etf_price=etf_quote.get('price', 0.0),
            etf_premium=etf_quote.get('premium', 0.0),
            reason=f"{limit_info.stock_name} 涨停 (+{limit_info.change_pct:.2f}%)，"
                   f"在 {best_etf.etf_name} 中持仓占比 {best_etf.weight_pct:.2f}% "
                   f"(排名第{best_etf.rank})",
            confidence=confidence,
            risk_level=risk_level,
            actual_weight=best_etf.weight,
            weight_rank=best_etf.rank,
            top10_ratio=best_etf.top10_ratio
        )

        logger.success(
            f"🎯 生成信号: {signal.stock_name} 涨停 -> 建议买入 {signal.etf_name}"
        )
        logger.success(
            f"   权重: {signal.actual_weight*100:.2f}%, 排名: 第{signal.weight_rank}, "
            f"置信度: {signal.confidence}"
        )

        return signal
