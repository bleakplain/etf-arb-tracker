"""
A股套利引擎

专门处理A股市场的涨停套利逻辑。
"""

from typing import List, Optional, Dict, Any, Tuple, TYPE_CHECKING
from loguru import logger
from dataclasses import dataclass

from backend.arbitrage.config import ArbitrageEngineConfig
from backend.arbitrage.models import TradingSignal
from backend.market import CandidateETF
from backend.market.interfaces import IQuoteFetcher, IETFHoldingProvider
from backend.arbitrage.strategy_registry import strategy_manager, StrategyManager
from backend.arbitrage.interfaces import FileMappingRepository, IMappingRepository
from backend.arbitrage.cn.strategies.interfaces import (
    IEventDetector,
    IFundSelector,
    ISignalFilter,
)
from backend.arbitrage.cn.strategy_executor import StrategyExecutor
from config import Config

# 延迟导入以避免循环依赖
if TYPE_CHECKING:
    from backend.signal.interfaces import ISignalEvaluator


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


class ArbitrageEngineCN:
    """
    A股套利引擎

    专门处理A股市场的涨停套利机会。
    当股票涨停时，通过买入包含该股票的ETF来获取套利机会。
    """

    def __init__(
        self,
        quote_fetcher: IQuoteFetcher,
        etf_holder_provider: IETFHoldingProvider,
        etf_holdings_provider: IETFHoldingProvider,
        etf_quote_provider: IQuoteFetcher,
        watch_securities: List[str] = None,
        engine_config: ArbitrageEngineConfig = None,
        signal_evaluator: 'ISignalEvaluator' = None,
        config: Config = None,
        strategy_manager_instance: StrategyManager = None,
        mapping_repository: IMappingRepository = None
    ):
        """
        初始化A股套利引擎

        Args:
            quote_fetcher: 行情数据获取器
            etf_holder_provider: ETF持仓关系提供者
            etf_holdings_provider: ETF持仓详情提供者
            etf_quote_provider: ETF行情提供者
            watch_securities: 监控的证券代码列表（默认从配置加载）
            engine_config: 套利引擎配置
            signal_evaluator: 信号评估器
            config: 应用配置
            strategy_manager_instance: 策略管理器（用于测试，默认使用全局实例）
            mapping_repository: 映射仓储（用于测试，默认使用文件仓储）
        """
        self._quote_fetcher = quote_fetcher
        self._etf_holder_provider = etf_holder_provider
        self._etf_holdings_provider = etf_holdings_provider
        self._etf_quote_provider = etf_quote_provider
        self._signal_evaluator = signal_evaluator
        self._config = config or Config.load()
        self._strategy_manager = strategy_manager_instance or strategy_manager
        self._mapping_repository = mapping_repository or FileMappingRepository("data/cn_stock_etf_mapping.json")

        # 加载默认监控列表
        if watch_securities is None:
            watch_securities = self._load_default_watch_securities(config)
        self._watch_securities = watch_securities

        # 加载或使用默认引擎配置
        self._engine_config = engine_config or self._get_default_config()

        # 验证配置有效性
        self._engine_config.assert_valid()

        # 策略组件
        self._event_detector: Optional[IEventDetector] = None
        self._fund_selector: Optional[IFundSelector] = None
        self._signal_filters: List[ISignalFilter] = []
        self._strategy_executor: Optional[StrategyExecutor] = None

        # 构建证券-基金映射
        self._security_fund_mapping: Dict[str, List[Dict]] = {}
        self._build_or_load_mapping()

        # 初始化策略
        self._init_strategies()
        self._init_strategy_executor()

        logger.info("套利引擎初始化完成")
        logger.info(f"引擎配置: {self._engine_config.to_dict()}")
        logger.info(f"监控证券数量: {len(self._watch_securities)}")
        logger.info(f"覆盖基金数量: {len(self.get_all_fund_codes())}")

        # 信号历史
        self._signal_history: List[TradingSignal] = []

    # ========================================================================
    # API便捷属性
    # ========================================================================

    @property
    def watch_stocks(self):
        """获取自选股列表（API兼容）"""
        return self._config.my_stocks if self._config else []

    @property
    def stock_fetcher(self):
        """获取股票行情获取器（API兼容）"""
        return self._quote_fetcher

    @property
    def etf_fetcher(self):
        """获取ETF行情获取器（API兼容）"""
        return self._etf_quote_provider

    @property
    def signal_history(self) -> List[TradingSignal]:
        """获取信号历史（API兼容）"""
        return self._signal_history

    def _get_default_config(self) -> ArbitrageEngineConfig:
        """获取A股默认引擎配置"""
        from backend.utils.constants import (
            CNMarketConstants,
            DEFAULT_MIN_TIME_TO_CLOSE,
        )

        return ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector="highest_weight",
            signal_filters=["time_filter_cn", "liquidity_filter"],
            event_config={'min_change_pct': CNMarketConstants.DEFAULT_LIMIT_UP_THRESHOLD},
            fund_config={'min_weight': CNMarketConstants.DEFAULT_MIN_WEIGHT},
            filter_configs={
                'time_filter_cn': {'min_time_to_close': DEFAULT_MIN_TIME_TO_CLOSE},
                'liquidity_filter': {'min_daily_amount': CNMarketConstants.DEFAULT_MIN_DAILY_AMOUNT}
            }
        )

    def _init_strategies(self) -> None:
        """初始化策略组件"""
        strategies = self._strategy_manager.create_from_registry(
            event_detector_name=self._engine_config.event_detector,
            fund_selector_name=self._engine_config.fund_selector,
            filter_names=self._engine_config.signal_filters,
            configs={
                'event_config': self._engine_config.event_config,
                'fund_config': self._engine_config.fund_config,
                'filter_configs': self._engine_config.filter_configs
            }
        )

        self._event_detector = strategies['event_detector']
        self._fund_selector = strategies['fund_selector']
        self._signal_filters = strategies['filters']

    def _init_strategy_executor(self) -> None:
        """初始化策略执行器"""
        if not all([self._event_detector, self._fund_selector]):
            logger.warning("策略组件未完全初始化，跳过策略执行器初始化")
            return

        self._strategy_executor = StrategyExecutor(
            event_detector=self._event_detector,
            fund_selector=self._fund_selector,
            signal_filters=self._signal_filters,
            etf_quote_provider=self._etf_quote_provider,
            signal_evaluator=self._signal_evaluator
        )

    def _build_or_load_mapping(self) -> None:
        """构建或加载证券-基金映射"""
        try:
            self._security_fund_mapping = self._mapping_repository.load_mapping() or {}
        except Exception as e:
            logger.warning(f"加载映射关系失败: {e}，将重新构建")
            self._security_fund_mapping = {}

        if self._security_fund_mapping:
            logger.info(f"使用已有映射关系，覆盖 {len(self._security_fund_mapping)} 只证券")
        else:
            logger.info("未找到已有映射，开始构建...")
            fund_codes = self._get_watch_fund_codes()
            self._security_fund_mapping = self._etf_holder_provider.build_stock_etf_mapping(
                self._watch_securities, fund_codes
            )
            self._mapping_repository.save_mapping(self._security_fund_mapping)
            logger.info(f"映射构建完成，覆盖 {len(self._security_fund_mapping)} 只证券")

    def _get_watch_fund_codes(self) -> List[str]:
        """获取监控的基金代码列表"""
        return [e.code for e in self._config.watch_etfs] if self._config else []

    def _load_default_watch_securities(self, config: Config) -> List[str]:
        """加载默认的A股监控列表"""
        if config and config.my_stocks:
            return [s.code for s in config.my_stocks]
        return []

    def get_all_fund_codes(self) -> List[str]:
        """获取所有相关基金代码"""
        fund_set = set()
        for fund_list in self._security_fund_mapping.values():
            for fund in fund_list:
                fund_set.add(fund['etf_code'])
        return list(fund_set)

    def get_eligible_funds(self, security_code: str) -> List[CandidateETF]:
        """获取符合条件的基金列表"""
        from backend.utils.code_utils import normalize_stock_code

        normalized_code = normalize_stock_code(security_code)
        mapped_funds = self._security_fund_mapping.get(normalized_code, [])

        if not mapped_funds:
            return []

        fund_names = {f['etf_code']: f['etf_name'] for f in mapped_funds}
        results = []

        for fund in mapped_funds:
            fund_code = fund['etf_code']
            holdings_data = self._etf_holdings_provider.get_etf_top_holdings(fund_code)
            if not holdings_data or not holdings_data.get('top_holdings'):
                continue

            holdings = holdings_data['top_holdings']
            rank = -1
            weight = 0
            for i, h in enumerate(holdings):
                if h['stock_code'] == normalized_code:
                    rank = i + 1
                    weight = h['weight']
                    break

            from backend.utils.constants import CNMarketConstants
            min_weight = self._engine_config.fund_config.get('min_weight', CNMarketConstants.DEFAULT_MIN_WEIGHT)
            if weight >= min_weight:
                results.append(CandidateETF(
                    etf_code=fund_code,
                    etf_name=fund_names.get(fund_code, f'ETF{fund_code}'),
                    weight=weight,
                    category='other',
                    rank=rank,
                    in_top10=rank > 0 and rank <= 10,
                    top10_ratio=holdings_data.get('total_weight', 0)
                ))

        results.sort(key=lambda x: x.weight, reverse=True)
        return results

    def _execute_strategy(
        self,
        quote: Dict,
        eligible_funds: List[CandidateETF]
    ) -> Tuple[Optional[TradingSignal], List[str]]:
        """
        执行策略组合

        Returns:
            (signal, logs) - (交易信号或None, 执行日志列表)
        """
        if not self._strategy_executor:
            return None, ["策略执行器未初始化"]

        return self._strategy_executor.execute(quote, eligible_funds)

    def scan_security(self, security_code: str) -> Optional[TradingSignal]:
        """扫描单个证券"""
        quote = self._quote_fetcher.get_stock_quote(security_code)
        if not quote:
            logger.debug(f"未获取到证券 {security_code} 的行情数据")
            return None

        eligible_funds = self.get_eligible_funds(security_code)
        if not eligible_funds:
            logger.debug(f"证券 {security_code} 没有符合条件的基金")
            return None

        signal, logs = self._execute_strategy(quote, eligible_funds)

        for log in logs:
            logger.info(log)

        return signal

    def scan_all(self) -> ScanResult:
        """扫描所有监控的A股证券"""
        logger.info("开始A股涨停套利扫描...")

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
                    self._signal_history.append(signal)
                    total_events += 1
                else:
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

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取当前策略信息"""
        return {
            'event_detector': self._event_detector.strategy_name if self._event_detector else '',
            'fund_selector': self._fund_selector.strategy_name if self._fund_selector else '',
            'signal_filters': [f.strategy_name for f in self._signal_filters]
        }

    def reload_strategy(self, new_config: ArbitrageEngineConfig) -> None:
        """重新加载策略配置"""
        self._engine_config = new_config
        self._init_strategies()
        self._init_strategy_executor()
        logger.info(f"策略已重新加载: {new_config.to_dict()}")

    def get_security_fund_mapping(self) -> Dict:
        """获取证券-基金映射关系"""
        return self._security_fund_mapping.copy()
