"""
A股回测引擎

复用 ArbitrageEngineCN 的策略链，使用历史数据进行回测。
"""

from typing import List, Optional, Callable, Dict, Any
from datetime import datetime
from loguru import logger

from config import Config, Stock
from backend.arbitrage.cn import ArbitrageEngineCN
from backend.arbitrage.models import TradingSignal
from backend.signal.evaluator import SignalEvaluatorFactory

from ..config import BacktestConfig
from ..clock import SimulationClock, TimeGranularity
from ..signal_recorder import SignalRecorder
from ..holdings_snapshot import HoldingsSnapshotManager
from ..metrics import BacktestResult
from .adapters.models import ETFReference
from .adapters.quote_fetcher import HistoricalQuoteFetcherAdapter
from .adapters.holding_provider import HistoricalHoldingProviderAdapter


class CNBacktestEngine:
    """
    A股回测引擎

    复用 ArbitrageEngineCN 的策略链，使用历史数据进行回测。
    """

    def __init__(
        self,
        config: BacktestConfig,
        stocks: List[Stock],
        etf_codes: List[str],
        app_config: Optional[Config] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ):
        """
        初始化回测引擎

        Args:
            config: 回测配置
            stocks: 股票列表
            etf_codes: ETF代码列表
            app_config: 应用配置（可选）
            progress_callback: 进度回调函数
        """
        self.config = config
        self.stocks = stocks
        self.etf_codes = etf_codes
        self.app_config = app_config or Config.load()
        self.progress_callback = progress_callback

        # 初始化时钟
        self.clock = SimulationClock(
            start_date=config.start_date,
            end_date=config.end_date,
            granularity=config.time_granularity
        )

        # 初始化信号记录器
        self.signal_recorder = SignalRecorder()

        # 初始化持仓快照管理器
        self.holdings_manager = HoldingsSnapshotManager(
            snapshot_dates=config.snapshot_dates,
            start_date=config.start_date,
            end_date=config.end_date
        )

        # 历史行情适配器（后续初始化）
        self.quote_fetcher_adapter: Optional[HistoricalQuoteFetcherAdapter] = None

        # 持仓数据适配器（后续初始化）
        self.holding_provider: Optional[HistoricalHoldingProviderAdapter] = None

        # A股套利引擎（后续初始化）
        self.arbitrage_engine: Optional[ArbitrageEngineCN] = None

        logger.info("A股回测引擎初始化完成")
        logger.info(f"时间范围: {config.start_date} -> {config.end_date}")
        logger.info(f"时间粒度: {config.time_granularity.value}")
        logger.info(f"股票数量: {len(stocks)}, ETF数量: {len(etf_codes)}")

    def initialize(self) -> None:
        """初始化回测环境"""
        from backend.backtest.data_loader import HistoricalDataLoader

        logger.info("=" * 60)
        logger.info("初始化A股回测环境...")
        logger.info("=" * 60)

        try:
            # 1. 初始化历史数据加载器
            stock_codes = [s.code for s in self.stocks]

            if self.progress_callback:
                self.progress_callback(0.1)

            data_loader = HistoricalDataLoader()

            # 2. 初始化历史行情适配器
            self.quote_fetcher_adapter = HistoricalQuoteFetcherAdapter(
                data_loader=data_loader,
                stock_codes=stock_codes,
                etf_codes=self.etf_codes,
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                granularity=self.config.time_granularity
            )

            # 加载历史数据
            def load_progress(loaded, total):
                if self.progress_callback:
                    load_progress = 0.1 + (loaded / total) * 0.3
                    self.progress_callback(min(load_progress, 0.4))
                if loaded % 50 == 0 or loaded == total:
                    logger.info(f"数据加载进度: {loaded}/{total} ({loaded*100//total if total > 0 else 0}%)")

            self.quote_fetcher_adapter.load_data(progress_callback=load_progress)
            logger.info("历史行情数据加载完成")

            if self.progress_callback:
                self.progress_callback(0.4)

            # 3. 加载持仓快照
            try:
                self.holdings_manager.load_snapshots(
                    stock_codes=stock_codes,
                    etf_codes=self.etf_codes
                )
                logger.info("持仓快照加载完成")
            except Exception as e:
                logger.warning(f"持仓快照加载失败（将使用模拟持仓数据）: {e}")

            if self.progress_callback:
                self.progress_callback(0.5)

            # 4. 创建持仓数据提供者适配器
            from .adapters.holding_provider import HistoricalHoldingProviderAdapter

            self.holding_provider = HistoricalHoldingProviderAdapter(
                snapshot_manager=self.holdings_manager,
                interpolation=self.config.interpolation
            )

            # 5. 初始化A股套利引擎（复用策略链）
            signal_evaluator = SignalEvaluatorFactory.create(
                self.config.evaluator_type,
                self.app_config.signal_evaluation
            )

            self.arbitrage_engine = ArbitrageEngineCN(
                quote_fetcher=self.quote_fetcher_adapter,
                etf_holder_provider=self.holding_provider,
                etf_holdings_provider=self.holding_provider,
                etf_quote_provider=self.quote_fetcher_adapter,
                signal_evaluator=signal_evaluator,
                config=self.app_config
            )

            logger.info("A股套利引擎初始化完成")
            if self.progress_callback:
                self.progress_callback(0.6)

            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"回测初始化失败: {e}")
            raise

    def run(self) -> BacktestResult:
        """
        运行回测

        Returns:
            回测结果
        """
        try:
            if not self.arbitrage_engine:
                self.initialize()

            logger.info("=" * 60)
            logger.info("开始回测...")
            logger.info("=" * 60)

            total_steps = self._estimate_total_steps()
            current_step = 0
            start_progress = 0.6
            progress_range = 0.4

            while self.clock.has_next():
                try:
                    # 推进时间
                    current_time = self.clock.advance()

                    # 更新适配器的当前时间
                    self.quote_fetcher_adapter.set_current_time(current_time)
                    self.holding_provider.set_current_time(current_time)

                    # 检查是否在交易时间
                    if not self.clock.is_trading_time():
                        continue

                    # 扫描所有股票
                    self._scan_stocks(current_time)

                    # 更新进度
                    current_step += 1
                    if self.progress_callback and total_steps > 0:
                        progress = start_progress + (current_step / total_steps) * progress_range
                        self.progress_callback(min(progress, 0.99))

                    # 日级别输出进度
                    if self.config.time_granularity == TimeGranularity.DAILY:
                        signal_count = self.signal_recorder.get_signal_count()
                        progress_pct = int(current_step * 100 / total_steps) if total_steps > 0 else 0
                        logger.info(
                            f"进度: {self.clock.current_date_str} ({progress_pct}%) - "
                            f"累计 {signal_count} 个信号"
                        )

                except Exception as e:
                    logger.error(f"回测过程中出错 (时间: {self.clock.current_datetime_str}): {e}")
                    continue

            # 生成结果
            logger.info("=" * 60)
            logger.info("回测完成，生成结果...")
            logger.info("=" * 60)

            if self.progress_callback:
                self.progress_callback(1.0)

            return self._generate_result()

        except Exception as e:
            logger.error(f"回测失败: {e}")
            raise RuntimeError(f"回测执行失败: {e}") from e

    def _scan_stocks(self, current_time: datetime) -> None:
        """扫描所有股票"""
        for stock in self.stocks:
            try:
                # 使用套利引擎扫描股票
                signal, logs = self.arbitrage_engine.scan_security(stock.code)

                if signal:
                    self.signal_recorder.record([signal], current_time)

            except Exception as e:
                logger.error(f"处理股票 {stock.code} ({stock.name}) 时出错: {e}")
                continue

    def _estimate_total_steps(self) -> int:
        """
        估算总步数

        日级回测：交易日数量
        分钟级回测：根据交易时长和粒度计算
        """
        if self.config.time_granularity == TimeGranularity.DAILY:
            return len(self.clock.trading_calendar)

        # 分钟级：计算实际步数
        # 每天交易4小时（240分钟）
        minutes_per_day = 240  # 9:30-11:30, 13:00-15:00
        granularity_minutes = self.config.time_granularity.delta_minutes
        slots_per_day = minutes_per_day / granularity_minutes
        return int(len(self.clock.trading_calendar) * slots_per_day)

    def _generate_result(self) -> BacktestResult:
        """生成回测结果"""
        from backend.backtest.metrics import StatisticsCalculator

        statistics = StatisticsCalculator.calculate(self.signal_recorder.signals)

        return BacktestResult(
            signals=self.signal_recorder.signals,
            statistics=statistics,
            date_range=self.clock.get_date_range(),
            time_granularity=self.config.time_granularity.value,
            parameters={
                "min_weight": self.config.min_weight,
                "min_time_to_close": self.config.min_time_to_close,
                "min_etf_volume": self.config.min_etf_volume,
                "evaluator_type": self.config.evaluator_type,
                "interpolation": self.config.interpolation,
                "stocks_count": len(self.stocks),
                "etfs_count": len(self.etf_codes)
            },
            data_details={
                "holdings_snapshot": self.holdings_manager.get_snapshot_summary()
            }
        )

    def get_progress(self) -> float:
        """获取当前进度"""
        return self.clock.get_progress()


def create_cn_backtest_engine(
    start_date: str,
    end_date: str,
    granularity: str = "daily",
    min_weight: Optional[float] = None,
    evaluator_type: str = "default",
    progress_callback: Optional[Callable[[float], None]] = None
) -> CNBacktestEngine:
    """
    创建A股回测引擎（便捷函数）

    Args:
        start_date: 开始日期 "YYYYMMDD"
        end_date: 结束日期 "YYYYMMDD"
        granularity: 时间粒度 "daily", "5m", "15m", "30m"
        min_weight: 最小持仓权重
        evaluator_type: 评估器类型
        progress_callback: 进度回调

    Returns:
        A股回测引擎实例
    """
    app_config = Config.load()

    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        time_granularity=TimeGranularity(granularity),
        min_weight=min_weight or app_config.strategy.min_weight,
        evaluator_type=evaluator_type,
        use_watchlist=True
    )

    return CNBacktestEngine(
        config=config,
        stocks=app_config.my_stocks,
        etf_codes=[e.code for e in app_config.watch_etfs],
        app_config=app_config,
        progress_callback=progress_callback
    )
