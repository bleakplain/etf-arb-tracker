"""
套利引擎 - 使用策略链处理套利机会

这是核心引擎，负责：
1. 加载策略链配置
2. 创建策略执行器
3. 扫描证券并生成信号
4. 向后兼容现有A股涨停套利逻辑
"""

from typing import List, Optional, Dict, Any
from loguru import logger
from dataclasses import dataclass

from backend.arbitrage.domain.interfaces import (
    IEventDetectorStrategy,
    IFundSelectionStrategy,
    ISignalFilterStrategy,
    EventInfo,
    ETFReference,
    TradingSignal,
    StrategyChainConfig
)
from backend.domain.interfaces import (
    IQuoteFetcher,
    IETFHolderProvider,
    IETFHoldingsProvider,
    IETFQuoteProvider,
    ISignalEvaluator
)
from backend.domain.value_objects import TradingSignal as VOT

from backend.engine.strategy_executor import StrategyExecutor
from backend.core.strategy_registry import strategy_manager
from config import Config


@dataclass
class ScanResult:
    """扫描结果"""
    signals: List[TradingSignal]
    total_scanned: int
    total_events: int
    filtered_count: int
    execution_logs: List[str]

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'signals': [
                {
                    'signal_id': s.signal_id,
                    'stock_code': s.stock_code,
                    'stock_name': s.stock_name,
                    'etf_code': s.etf_code,
                    'etf_name': s.etf_name,
                    'timestamp': s.timestamp
                }
                for s in self.signals
            ],
            'total_scanned': self.total_scanned,
            'total_events': self.total_events,
            'filtered_count': self.filtered_count,
            'execution_logs': self.execution_logs
        }


class ArbitrageEngine:
    """
    套利引擎

    使用可插拔的策略链来处理套利机会。
    支持配置文件驱动的策略选择。
    """

    def __init__(
        self,
        quote_fetcher: IQuoteFetcher,
        etf_holder_provider: IETFHolderProvider,
        etf_holdings_provider: IETFHoldingsProvider,
        etf_quote_provider: IETFQuoteProvider,
        watch_securities: List[str],
        strategy_config: StrategyChainConfig = None,
        signal_evaluator: ISignalEvaluator = None,
        config: Config = None
    ):
        """
        初始化套利引擎

        Args:
            quote_fetcher: 行情数据获取器
            etf_holder_provider: ETF持仓关系提供者
            etf_holdings_provider: ETF持仓详情提供者
            etf_quote_provider: ETF行情提供者
            watch_securities: 监控的证券代码列表
            strategy_config: 策略链配置
            signal_evaluator: 信号评估器
            config: 应用配置
        """
        self._quote_fetcher = quote_fetcher
        self._etf_holder_provider = etf_holder_provider
        self._etf_holdings_provider = etf_holdings_provider
        self._etf_quote_provider = etf_quote_provider
        self._watch_securities = watch_securities
        self._signal_evaluator = signal_evaluator
        self._config = config or Config.load()

        # 加载或使用默认策略配置
        self._strategy_config = strategy_config or self._load_default_config()

        # 创建策略执行器
        self._executor = self._create_executor()

        # 构建证券-基金映射
        self._security_fund_mapping: Dict[str, List[Dict]] = {}
        self._build_or_load_mapping()

        logger.info("套利引擎初始化完成")
        logger.info(f"策略配置: {self._strategy_config.to_dict()}")
        logger.info(f"监控证券数量: {len(self._watch_securities)}")
        logger.info(f"覆盖基金数量: {len(self.get_all_fund_codes())}")

    def _load_default_config(self) -> StrategyChainConfig:
        """加载默认策略配置（A股涨停套利）"""
        return StrategyChainConfig(
            event_detector="limit_up",
            fund_selector="highest_weight",
            signal_filters=["time_filter", "liquidity_filter"],
            event_config={'min_change_pct': 0.095},
            fund_config={'min_weight': 0.05},
            filter_configs={
                'time_filter': {'min_time_to_close': 1800},
                'liquidity_filter': {'min_daily_amount': 50000000}
            }
        )

    def _create_executor(self) -> StrategyExecutor:
        """创建策略执行器"""
        # 从注册表获取策略实例
        strategies = strategy_manager.create_from_registry(
            event_detector_name=self._strategy_config.event_detector,
            fund_selector_name=self._strategy_config.fund_selector,
            filter_names=self._strategy_config.signal_filters,
            configs={
                'event_config': self._strategy_config.event_config,
                'fund_config': self._strategy_config.fund_config,
                'filter_configs': self._strategy_config.filter_configs
            }
        )

        return StrategyExecutor(
            event_detector=strategies['event_detector'],
            fund_selector=strategies['fund_selector'],
            signal_filters=strategies['filters']
        )

    def _build_or_load_mapping(self) -> None:
        """构建或加载证券-基金映射"""
        mapping_file = "data/stock_etf_mapping.json"

        # 尝试加载已有映射
        try:
            self._security_fund_mapping = self._etf_holder_provider.load_mapping(mapping_file) or {}
        except Exception:
            self._security_fund_mapping = {}

        if self._security_fund_mapping:
            logger.info(f"使用已有映射关系，覆盖 {len(self._security_fund_mapping)} 只证券")
        else:
            logger.info("未找到已有映射，开始构建...")
            # 这里需要获取所有基金代码
            fund_codes = [e.code for e in self._config.watch_etfs] if self._config else []
            self._security_fund_mapping = self._etf_holder_provider.build_stock_etf_mapping(
                self._watch_securities, fund_codes
            )
            self._etf_holder_provider.save_mapping(self._security_fund_mapping, mapping_file)
            logger.info(f"映射构建完成，覆盖 {len(self._security_fund_mapping)} 只证券")

    def get_all_fund_codes(self) -> List[str]:
        """获取所有相关基金代码"""
        fund_set = set()
        for fund_list in self._security_fund_mapping.values():
            for fund in fund_list:
                fund_set.add(fund['etf_code'])
        return list(fund_set)

    def get_eligible_funds(self, security_code: str) -> List[ETFReference]:
        """
        获取符合条件的基金列表

        Args:
            security_code: 证券代码

        Returns:
            符合条件的ETF引用列表
        """
        from backend.utils.code_utils import normalize_stock_code
        from backend.domain.value_objects import ETFReference

        normalized_code = normalize_stock_code(security_code)
        mapped_funds = self._security_fund_mapping.get(normalized_code, [])

        if not mapped_funds:
            return []

        # 获取基金名称
        fund_names = {f['etf_code']: f['etf_name'] for f in mapped_funds}

        # 获取真实持仓权重
        results = []
        for fund in mapped_funds:
            fund_code = fund['etf_code']

            # 获取持仓权重
            holdings_data = self._etf_holdings_provider.get_etf_top_holdings(fund_code)
            if not holdings_data or not holdings_data.get('top_holdings'):
                continue

            holdings = holdings_data['top_holdings']

            # 查找证券在持仓中的位置
            rank = -1
            weight = 0
            for i, h in enumerate(holdings):
                if h['stock_code'] == normalized_code:
                    rank = i + 1
                    weight = h['weight']
                    break

            # 根据配置筛选
            min_weight = self._strategy_config.fund_config.get('min_weight', 0.05)
            if weight >= min_weight:
                results.append(ETFReference(
                    etf_code=fund_code,
                    etf_name=fund_names.get(fund_code, f'ETF{fund_code}'),
                    weight=weight,
                    category='other',  # 简化，实际应该从配置获取
                    rank=rank,
                    in_top10=rank > 0 and rank <= 10,
                    top10_ratio=holdings_data.get('total_weight', 0)
                ))

        # 按权重降序排序
        results.sort(key=lambda x: x.weight, reverse=True)
        return results

    def scan_security(self, security_code: str) -> Optional[TradingSignal]:
        """
        扫描单个证券

        Args:
            security_code: 证券代码

        Returns:
            交易信号或None
        """
        # 获取行情
        quote = self._quote_fetcher.get_stock_quote(security_code)
        if not quote:
            logger.debug(f"未获取到证券 {security_code} 的行情数据")
            return None

        # 获取符合条件的基金
        eligible_funds = self.get_eligible_funds(security_code)
        if not eligible_funds:
            logger.debug(f"证券 {security_code} 没有符合条件的基金")
            return None

        # 执行策略链
        signal, logs = self._executor.execute(
            quote=quote,
            eligible_funds=eligible_funds,
            etf_quote_provider=self._etf_quote_provider,
            signal_evaluator=self._signal_evaluator
        )

        # 记录日志
        for log in logs:
            logger.info(log)

        return signal

    def scan_all(self) -> ScanResult:
        """
        扫描所有监控的证券

        Returns:
            扫描结果
        """
        signals = []
        total_events = 0
        filtered_count = 0
        all_logs = []

        logger.info(f"开始扫描 {len(self._watch_securities)} 只证券...")
        all_logs.append(f"开始扫描 {len(self._watch_securities)} 只证券...")

        for security_code in self._watch_securities:
            try:
                signal = self.scan_security(security_code)
                if signal:
                    signals.append(signal)
                    total_events += 1
                else:
                    # 即使没有信号，也可能是检测到了事件但被过滤
                    filtered_count += 1

            except Exception as e:
                logger.error(f"扫描证券 {security_code} 失败: {e}")
                all_logs.append(f"✗ 扫描失败 {security_code}: {e}")

        all_logs.append(f"扫描完成，生成 {len(signals)} 个信号")

        result = ScanResult(
            signals=signals,
            total_scanned=len(self._watch_securities),
            total_events=total_events,
            filtered_count=filtered_count,
            execution_logs=all_logs
        )

        logger.info(f"扫描完成: 总计{result.total_scanned}只, 事件{result.total_events}个, "
                   f"信号{len(result.signals)}个")

        return result

    def get_strategy_info(self) -> Dict:
        """获取当前策略信息"""
        return self._executor.strategy_info

    def reload_strategy(self, new_config: StrategyChainConfig) -> None:
        """
        重新加载策略配置

        Args:
            new_config: 新的策略链配置
        """
        self._strategy_config = new_config
        self._executor = self._create_executor()
        logger.info(f"策略已重新加载: {new_config.to_dict()}")

    def get_security_fund_mapping(self) -> Dict:
        """获取证券-基金映射关系"""
        return self._security_fund_mapping.copy()
