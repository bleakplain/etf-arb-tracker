"""
回测引擎核心

协调整个回测流程，复用现有策略组件。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from loguru import logger

from config import Config, Stock
from backend.domain.value_objects import ETFReference
from backend.strategy.limit_checker import LimitChecker
from backend.strategy.signal_generator import SignalGenerator
from backend.strategy.signal_evaluators import SignalEvaluatorFactory
from backend.data.sources.historical_source import HistoricalQuoteFetcher

from .clock import TimeGranularity, SimulationClock
from .signal_recorder import SignalRecorder
from .holdings_snapshot import HoldingsSnapshotManager
from .metrics import BacktestResult


@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: str
    end_date: str
    time_granularity: TimeGranularity = TimeGranularity.DAILY
    min_weight: float = 0.05
    min_time_to_close: int = 1800
    min_etf_volume: float = 50000000
    evaluator_type: str = "default"
    snapshot_dates: Optional[List[str]] = None
    interpolation: str = "linear"
    use_watchlist: bool = True

    # 常量定义
    MIN_DATE = "20000101"  # A股 earliest reasonable date
    MAX_DATE = "20991231"  # Future max date
    MIN_WEIGHT_THRESHOLD = 0.001
    MAX_WEIGHT_THRESHOLD = 1.0

    def __post_init__(self):
        """配置验证"""
        self._validate_dates()
        self._validate_weights()
        self._validate_interpolation()

    def _validate_dates(self) -> None:
        """验证日期范围"""
        try:
            start_dt = datetime.strptime(self.start_date, "%Y%m%d")
            end_dt = datetime.strptime(self.end_date, "%Y%m%d")

            # 检查日期格式和范围
            if start_dt < datetime.strptime(self.MIN_DATE, "%Y%m%d"):
                raise ValueError(f"开始日期不能早于 {self.MIN_DATE}")
            if end_dt > datetime.strptime(self.MAX_DATE, "%Y%m%d"):
                raise ValueError(f"结束日期不能晚于 {self.MAX_DATE}")

            # 检查开始日期必须早于或等于结束日期
            if start_dt > end_dt:
                raise ValueError(f"开始日期 {self.start_date} 不能晚于结束日期 {self.end_date}")

        except ValueError as e:
            if "time data" in str(e):
                raise ValueError(f"日期格式错误，应为YYYYMMDD格式，例如: 20240101")
            raise

    def _validate_weights(self) -> None:
        """验证权重参数"""
        if not (self.MIN_WEIGHT_THRESHOLD <= self.min_weight <= self.MAX_WEIGHT_THRESHOLD):
            raise ValueError(
                f"权重必须在 {self.MIN_WEIGHT_THRESHOLD} 到 {self.MAX_WEIGHT_THRESHOLD} 之间"
            )

    def _validate_interpolation(self) -> None:
        """验证插值方式"""
        valid_interpolations = ["linear", "step"]
        if self.interpolation not in valid_interpolations:
            raise ValueError(f"插值方式必须是 {valid_interpolations} 之一")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacktestConfig":
        """从字典创建配置"""
        granularity = TimeGranularity(data.get("time_granularity", "daily"))

        # 创建配置对象（会自动触发__post_init__验证）
        return cls(
            start_date=data["start_date"],
            end_date=data["end_date"],
            time_granularity=granularity,
            min_weight=data.get("min_weight", 0.05),
            min_time_to_close=data.get("min_time_to_close", 1800),
            min_etf_volume=data.get("min_etf_volume", 50000000),
            evaluator_type=data.get("evaluator_type", "default"),
            snapshot_dates=data.get("snapshot_dates"),
            interpolation=data.get("interpolation", "linear"),
            use_watchlist=data.get("use_watchlist", True)
        )


class BacktestEngine:
    """
    回测引擎

    协调整个回测流程，复用现有策略组件。
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
            snapshot_dates=config.snapshot_dates
        )

        # 历史行情获取器（后续初始化）
        self.quote_fetcher: Optional[HistoricalQuoteFetcher] = None

        # 策略组件（后续初始化）
        self.limit_checker: Optional[LimitChecker] = None
        self.signal_generator: Optional[SignalGenerator] = None

        logger.info("回测引擎初始化完成")
        logger.info(f"时间范围: {config.start_date} -> {config.end_date}")
        logger.info(f"时间粒度: {config.time_granularity.value}")
        logger.info(f"股票数量: {len(stocks)}, ETF数量: {len(etf_codes)}")

    def initialize(self) -> None:
        """初始化回测环境"""
        import traceback

        logger.info("=" * 60)
        logger.info("初始化回测环境...")
        logger.info("=" * 60)

        try:
            # 1. 初始化历史行情获取器
            stock_codes = [s.code for s in self.stocks]
            total_symbols = len(stock_codes) + len(self.etf_codes)
            logger.info(f"需要加载 {len(stock_codes)} 只股票和 {len(self.etf_codes)} 个ETF的历史数据")

            # 报告初始化进度
            if self.progress_callback:
                self.progress_callback(0.1)  # 初始化阶段 10%

            self.quote_fetcher = HistoricalQuoteFetcher(
                stock_codes=stock_codes,
                etf_codes=self.etf_codes,
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                granularity=self.config.time_granularity
            )

            try:
                # 创建进度回调用于数据加载
                def load_progress(loaded: int, total: int):
                    if self.progress_callback:
                        # 数据加载占总进度的 30% (10%-40%)
                        load_progress = 0.1 + (loaded / total) * 0.3
                        self.progress_callback(min(load_progress, 0.4))
                    if loaded % 50 == 0 or loaded == total:
                        logger.info(f"数据加载进度: {loaded}/{total} ({loaded*100//total if total > 0 else 0}%)")

                self.quote_fetcher.load_data(progress_callback=load_progress)
                logger.info("历史行情数据加载完成")

                if self.progress_callback:
                    self.progress_callback(0.4)  # 数据加载完成 40%
            except Exception as e:
                logger.error(
                    f"历史数据加载失败: {e}\n"
                    f"堆栈信息:\n{traceback.format_exc()}"
                )
                raise RuntimeError(f"无法加载历史数据: {e}") from e

            # 2. 加载持仓快照
            try:
                self.holdings_manager.load_snapshots(
                    stock_codes=stock_codes,
                    etf_codes=self.etf_codes
                )
                logger.info("持仓快照加载完成")
            except Exception as e:
                logger.warning(
                    f"持仓快照加载失败（将使用模拟持仓数据）: {e}\n"
                    f"堆栈信息:\n{traceback.format_exc()}"
                )
                # 不中断回测，继续使用模拟持仓

            if self.progress_callback:
                self.progress_callback(0.5)  # 持仓加载完成 50%

            # 3. 初始化策略组件
            try:
                signal_evaluator = SignalEvaluatorFactory.create(
                    self.config.evaluator_type,
                    self.app_config.signal_evaluation
                )

                self.limit_checker = LimitChecker(self.quote_fetcher)

                # 创建一个简单的ETF行情提供者适配器
                etf_quote_provider = _ETFQuoteProviderAdapter(self.quote_fetcher)

                self.signal_generator = SignalGenerator(
                    quote_fetcher=self.quote_fetcher,
                    etf_quote_provider=etf_quote_provider,
                    signal_evaluator=signal_evaluator,
                    min_time_to_close=self.config.min_time_to_close,
                    min_etf_volume=self.config.min_etf_volume
                )

                logger.info("策略组件初始化完成")
            except Exception as e:
                logger.error(
                    f"策略组件初始化失败: {e}\n"
                    f"堆栈信息:\n{traceback.format_exc()}"
                )
                raise RuntimeError(f"策略组件初始化失败: {e}") from e

            if self.progress_callback:
                self.progress_callback(0.6)  # 策略组件初始化完成 60%

            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"回测初始化失败: {e}")
            raise

    def run(self) -> BacktestResult:
        """
        运行回测

        Returns:
            回测结果

        Raises:
            RuntimeError: 如果回测初始化失败或数据加载失败
            ValueError: 如果配置参数无效
        """
        import traceback

        try:
            if not self.quote_fetcher:
                self.initialize()

            logger.info("=" * 60)
            logger.info("开始回测...")
            logger.info("=" * 60)

            total_steps = self._estimate_total_steps()
            current_step = 0

            # 回测执行阶段占总进度的 40% (60%-100%)
            start_progress = 0.6
            progress_range = 0.4

            while self.clock.has_next():
                try:
                    # 推进时间
                    current_time = self.clock.advance()

                    # 更新行情获取器的当前时间
                    self.quote_fetcher.set_current_time(current_time)

                    # 检查是否在交易时间
                    if not self.clock.is_trading_time():
                        continue

                    # 扫描所有股票
                    self._scan_stocks(current_time)

                    # 更新进度
                    current_step += 1
                    if self.progress_callback and total_steps > 0:
                        progress = start_progress + (current_step / total_steps) * progress_range
                        self.progress_callback(min(progress, 0.99))  # 保留1%给结果生成

                    # 日级别输出进度
                    if self.config.time_granularity == TimeGranularity.DAILY:
                        signal_count = self.signal_recorder.get_signal_count()
                        progress_pct = int(current_step * 100 / total_steps) if total_steps > 0 else 0
                        logger.info(
                            f"进度: {self.clock.current_date_str} ({progress_pct}%) - "
                            f"累计 {signal_count} 个信号"
                        )

                except Exception as e:
                    logger.error(
                        f"回测过程中出错 (时间: {self.clock.current_datetime_str}): {e}\n"
                        f"堆栈信息:\n{traceback.format_exc()}"
                    )
                    # 继续执行，不中断整个回测
                    continue

            # 生成结果
            logger.info("=" * 60)
            logger.info("回测完成，生成结果...")
            logger.info("=" * 60)

            if self.progress_callback:
                self.progress_callback(1.0)

            return self._generate_result()

        except Exception as e:
            logger.error(
                f"回测失败: {e}\n"
                f"配置参数:\n"
                f"  开始日期: {self.config.start_date}\n"
                f"  结束日期: {self.config.end_date}\n"
                f"  时间粒度: {self.config.time_granularity.value}\n"
                f"  股票数量: {len(self.stocks)}\n"
                f"  ETF数量: {len(self.etf_codes)}\n"
                f"堆栈信息:\n{traceback.format_exc()}"
            )
            raise RuntimeError(f"回测执行失败: {e}") from e

    def _scan_stocks(self, current_time: datetime) -> None:
        """扫描所有股票"""
        import traceback

        for stock in self.stocks:
            try:
                # 检查是否涨停
                limit_info = self.limit_checker.check_limit_up(stock.code)
                if not limit_info:
                    continue

                # 获取符合条件的ETF
                etf_refs = self._get_eligible_etfs(stock.code, current_time)
                if not etf_refs:
                    logger.debug(
                        f"{stock.name} 涨停但无符合条件的ETF "
                        f"(权重>={self.config.min_weight*100:.0f}%)"
                    )
                    continue

                # 生成信号
                signal = self.signal_generator.generate_signal(limit_info, etf_refs)
                if signal:
                    self.signal_recorder.record([signal], current_time)

            except Exception as e:
                logger.error(
                    f"处理股票 {stock.code} ({stock.name}) 时出错 "
                    f"(时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}): {e}\n"
                    f"堆栈信息:\n{traceback.format_exc()}"
                )
                # 继续处理下一只股票

    def _get_eligible_etfs(
        self,
        stock_code: str,
        current_time: datetime
    ) -> List[ETFReference]:
        """获取符合条件的ETF"""
        etf_refs = self.holdings_manager.get_holdings_at_date(
            stock_code,
            current_time,
            interpolation=self.config.interpolation
        )

        # 按权重筛选
        return [
            ref for ref in etf_refs
            if ref.weight >= self.config.min_weight
        ]

    def _estimate_total_steps(self) -> int:
        """估算总步数"""
        if self.config.time_granularity == TimeGranularity.DAILY:
            return len(self.clock.trading_calendar)
        return 1000  # 分钟级别的估算值

    def _generate_result(self) -> BacktestResult:
        """生成回测结果"""
        statistics = self.signal_recorder.get_statistics()

        # 收集数据详情
        data_details = self._collect_data_details()

        return BacktestResult(
            signals=self.signal_recorder.get_signals(),
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
            data_details=data_details
        )

    def _collect_data_details(self) -> Dict[str, Any]:
        """收集数据详情"""
        details = {
            "data_source": {
                "name": "历史行情数据",
                "description": "使用历史K线数据进行回测",
                "stocks_data": {},
                "etfs_data": {},
                "holdings_snapshots": {}
            },
            "trading_calendar": {
                "total_days": len(self.clock.trading_calendar),
                "trading_days": list(self.clock.trading_calendar)[:10],
                "description": f"共{len(self.clock.trading_calendar)}个交易日"
            },
            "scan_details": {
                "total_scans": len(self.clock.trading_calendar) * len(self.stocks),
                "stocks_with_limit_up": len(
                    set(s.stock_code for s in self.signal_recorder.get_signals())
                ),
                "signals_generated": len(self.signal_recorder.get_signals())
            }
        }

        if self.quote_fetcher:
            # 收集股票数据详情（限制前10个）
            self._collect_quote_details(
                self.quote_fetcher._stock_data,
                self.stocks[:10],
                details["data_source"]["stocks_data"]
            )

            # 收集ETF数据详情（限制前10个）
            self._collect_etf_details(
                self.quote_fetcher._etf_data,
                self.etf_codes[:10],
                details["data_source"]["etfs_data"]
            )

        # 收集持仓快照详情（限制前10个股票）
        if self.holdings_manager:
            for stock in self.stocks[:10]:
                snapshots = self.holdings_manager.snapshots.get(stock.code, {})
                if snapshots:
                    details["data_source"]["holdings_snapshots"][stock.code] = {
                        "name": stock.name,
                        "snapshot_count": len(snapshots),
                        "snapshot_dates": sorted(list(snapshots.keys()))[:5]
                    }

        return details

    def _collect_quote_details(
        self,
        data_source: Dict,
        stocks: List[Stock],
        output: Dict
    ) -> None:
        """收集股票行情数据详情"""
        for stock in stocks:
            stock_data = data_source.get(stock.code)
            if not stock_data:
                continue

            dates = list(stock_data.keys())
            output[stock.code] = {
                "name": stock.name,
                "data_points": len(stock_data),
                "date_range": {
                    "start": dates[0].strftime("%Y-%m-%d") if dates else "N/A",
                    "end": dates[-1].strftime("%Y-%m-%d") if dates else "N/A"
                }
            }

    def _collect_etf_details(
        self,
        data_source: Dict,
        etf_codes: List[str],
        output: Dict
    ) -> None:
        """收集ETF行情数据详情"""
        for etf_code in etf_codes:
            etf_data = data_source.get(etf_code)
            if not etf_data:
                continue

            dates = list(etf_data.keys())
            output[etf_code] = {
                "data_points": len(etf_data),
                "date_range": {
                    "start": dates[0].strftime("%Y-%m-%d") if dates else "N/A",
                    "end": dates[-1].strftime("%Y-%m-%d") if dates else "N/A"
                }
            }

    def get_progress(self) -> float:
        """获取当前进度"""
        return self.clock.get_progress()


class _ETFQuoteProviderAdapter:
    """
    ETF行情提供者适配器

    适配HistoricalQuoteFetcher以供SignalGenerator使用
    """

    def __init__(self, quote_fetcher: HistoricalQuoteFetcher):
        self.quote_fetcher = quote_fetcher

    def get_etf_quote(self, etf_code: str) -> Optional[Dict]:
        """获取ETF行情"""
        return self.quote_fetcher.get_etf_quote(etf_code)

    def get_etf_batch_quotes(self, etf_codes: List[str]) -> Dict[str, Dict]:
        """批量获取ETF行情"""
        return self.quote_fetcher.get_etf_batch_quotes(etf_codes)

    def check_liquidity(self, etf_code: str, min_amount: float) -> bool:
        """检查流动性"""
        return self.quote_fetcher.check_liquidity(etf_code, min_amount)


def create_backtest_engine(
    start_date: str,
    end_date: str,
    granularity: str = "daily",
    min_weight: Optional[float] = None,
    evaluator_type: str = "default",
    progress_callback: Optional[Callable[[float], None]] = None
) -> BacktestEngine:
    """
    创建回测引擎（便捷函数）

    Args:
        start_date: 开始日期 "YYYYMMDD"
        end_date: 结束日期 "YYYYMMDD"
        granularity: 时间粒度 "daily", "5m", "15m", "30m"
        min_weight: 最小持仓权重
        evaluator_type: 评估器类型
        progress_callback: 进度回调

    Returns:
        回测引擎实例
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

    return BacktestEngine(
        config=config,
        stocks=app_config.my_stocks,
        etf_codes=[e.code for e in app_config.watch_etfs],
        app_config=app_config,
        progress_callback=progress_callback
    )
