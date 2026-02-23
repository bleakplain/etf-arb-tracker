"""
A股回测引擎
"""

from typing import List, Dict, Optional, Callable
from datetime import datetime
from loguru import logger

from config import Config
from backend.arbitrage.cn import ArbitrageEngineCN
from backend.arbitrage.models import TradingSignal
from backend.signal.evaluator import SignalEvaluatorFactory

from ..config import BacktestConfig
from .data_provider import BacktestDataProvider


class CNBacktestEngine:
    """
    A股回测引擎

    使用历史数据遍历交易日，通过 ArbitrageEngineCN 生成交易信号。
    """

    def __init__(
        self,
        config: BacktestConfig,
        app_config: Optional[Config] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ):
        """
        初始化回测引擎

        Args:
            config: 回测配置
            app_config: 应用配置（用于信号评估器）
            progress_callback: 进度回调函数 (0.0 - 1.0)
        """
        self.config = config
        self.app_config = app_config or Config.load()
        self.progress_callback = progress_callback

        # 组件
        self.data_provider: Optional[BacktestDataProvider] = None
        self.arbitrage_engine: Optional[ArbitrageEngineCN] = None

        # 结果存储
        self.signals: List[TradingSignal] = []
        self.signal_dates: List[str] = []

        logger.info(f"回测引擎初始化: {config.start_date} -> {config.end_date}")
        logger.info(f"股票: {len(config.stock_codes)}, ETF: {len(config.etf_codes)}")

    def initialize(
        self,
        quotes: Dict[str, Dict[str, dict]],
        holdings: Optional[Dict[str, List]] = None
    ) -> None:
        """
        初始化回测环境

        Args:
            quotes: 历史行情数据 {date: {code: quote_dict}}
            holdings: 持仓数据 {stock_code: [CandidateETF, ...]}（可选）
        """
        logger.info("初始化回测环境...")

        # 1. 创建数据提供者
        self.data_provider = BacktestDataProvider(
            quotes=quotes,
            holdings=holdings,
            etf_codes=self.config.etf_codes,
            use_mock_holdings=self.config.use_mock_data,
            mock_etf_count=self.config.mock_etf_count
        )

        # 2. 创建信号评估器
        signal_evaluator = SignalEvaluatorFactory.create(
            self.config.evaluator_type,
            self.app_config.signal_evaluation
        )

        # 3. 创建套利引擎
        self.arbitrage_engine = ArbitrageEngineCN(
            quote_fetcher=self.data_provider,
            etf_holder_provider=self.data_provider,
            etf_holdings_provider=self.data_provider,
            etf_quote_provider=self.data_provider,
            signal_evaluator=signal_evaluator,
            config=self.app_config
        )

        logger.info(f"回测环境初始化完成")
        logger.info(f"数据摘要: {self.data_provider.get_data_summary()}")

    def run(self) -> Dict:
        """
        运行回测

        Returns:
            回测结果字典
        """
        if not self.data_provider or not self.arbitrage_engine:
            raise RuntimeError("请先调用 initialize() 初始化回测环境")

        logger.info("=" * 50)
        logger.info("开始回测...")
        logger.info("=" * 50)

        trading_days = self.config.trading_days
        total_days = len(trading_days)

        for i, date in enumerate(trading_days):
            try:
                # 更新数据提供者的当前日期
                self.data_provider.set_current_date(date)

                # 扫描所有股票
                for stock_code in self.config.stock_codes:
                    try:
                        signal = self.arbitrage_engine.analyze_security(stock_code)

                        if signal:
                            self.signals.append(signal)
                            self.signal_dates.append(date)

                    except Exception as e:
                        logger.debug(f"处理股票 {stock_code} 在 {date} 时出错: {e}")

                # 更新进度
                if self.progress_callback:
                    progress = (i + 1) / total_days
                    self.progress_callback(progress)

                # 每处理 10 个交易日输出一次进度
                if (i + 1) % 10 == 0 or (i + 1) == total_days:
                    logger.info(
                        f"进度: {date} ({i+1}/{total_days}={int((i+1)/total_days*100)}%) - "
                        f"累计 {len(self.signals)} 个信号"
                    )

            except Exception as e:
                logger.error(f"处理日期 {date} 时出错: {e}")
                continue

        logger.info("=" * 50)
        logger.info("回测完成")
        logger.info("=" * 50)

        return self._generate_result()

    def _generate_result(self) -> Dict:
        """生成回测结果"""
        # 统计每个股票的信号数量
        stock_signal_count: Dict[str, int] = {}
        for signal in self.signals:
            stock_code = signal.stock_code
            stock_signal_count[stock_code] = stock_signal_count.get(stock_code, 0) + 1

        # 统计每个 ETF 的出现次数
        etf_signal_count: Dict[str, int] = {}
        for signal in self.signals:
            for etf in signal.candidate_etfs:
                etf_code = etf.etf_code
                etf_signal_count[etf_code] = etf_signal_count.get(etf_code, 0) + 1

        # 按日期统计
        daily_signal_count: Dict[str, int] = {}
        for date in self.signal_dates:
            daily_signal_count[date] = daily_signal_count.get(date, 0) + 1

        return {
            "total_signals": len(self.signals),
            "stock_signal_count": stock_signal_count,
            "etf_signal_count": etf_signal_count,
            "daily_signal_count": daily_signal_count,
            "signals": [
                {
                    "date": self.signal_dates[i],
                    "stock_code": s.stock_code,
                    "stock_name": s.stock_name,
                    "etf_count": len(s.candidate_etfs),
                    "confidence": s.confidence,
                    "candidate_etfs": [
                        {
                            "etf_code": e.etf_code,
                            "etf_name": e.etf_name,
                            "weight": e.weight
                        }
                        for e in s.candidate_etfs
                    ]
                }
                for i, s in enumerate(self.signals)
            ],
            "config": {
                "start_date": self.config.start_date,
                "end_date": self.config.end_date,
                "stocks_count": len(self.config.stock_codes),
                "etfs_count": len(self.config.etf_codes),
                "using_mock_holdings": self.config.use_mock_data
            },
            "data_summary": self.data_provider.get_data_summary()
        }


def create_cn_backtest_engine(
    start_date: str,
    end_date: str,
    stock_codes: Optional[List[str]] = None,
    etf_codes: Optional[List[str]] = None,
    progress_callback: Optional[Callable[[float], None]] = None
) -> CNBacktestEngine:
    """
    创建 A股回测引擎

    Args:
        start_date: 开始日期 "YYYYMMDD"
        end_date: 结束日期 "YYYYMMDD"
        stock_codes: 股票代码列表（默认使用配置文件）
        etf_codes: ETF 代码列表（默认使用配置文件）
        progress_callback: 进度回调

    Returns:
        回测引擎实例
    """
    app_config = Config.load()

    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        stock_codes=stock_codes or [s.code for s in app_config.my_stocks],
        etf_codes=etf_codes or [e.code for e in app_config.watch_etfs],
        use_mock_data=True
    )

    return CNBacktestEngine(
        config=config,
        app_config=app_config,
        progress_callback=progress_callback
    )
