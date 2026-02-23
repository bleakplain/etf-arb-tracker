"""
LimitUpMonitor - A股涨停监控器

作为 ArbitrageEngineCN 的包装器，为 API 提供统一的监控接口
"""

from typing import List, Optional
from loguru import logger

from backend.arbitrage.cn import ArbitrageEngineCN
from backend.arbitrage.cn.factory import ArbitrageEngineFactory
from backend.arbitrage.config import ArbitrageEngineConfig
from backend.market.interfaces import IQuoteFetcher, IETFHoldingProvider
from backend.signal.interfaces import ISignalEvaluator
from config import Config


class LimitUpMonitor:
    """
    A股涨停监控器

    包装 ArbitrageEngineCN，为 API 提供统一的监控接口。
    提供自选股列表、行情获取、信号历史等功能。
    """

    def __init__(
        self,
        engine: ArbitrageEngineCN,
        config: Config
    ):
        """
        初始化监控器

        Args:
            engine: 套利引擎实例
            config: 应用配置
        """
        self._engine = engine
        self._config = config
        self._signal_history: List = []

    @property
    def watch_stocks(self) -> List:
        """获取自选股列表"""
        return self._config.my_stocks

    @property
    def stock_fetcher(self) -> IQuoteFetcher:
        """获取股票行情获取器"""
        return self._engine._quote_fetcher

    @property
    def etf_fetcher(self):
        """获取ETF行情获取器"""
        return self._engine._etf_quote_provider

    @property
    def signal_history(self) -> List:
        """获取信号历史"""
        return self._signal_history

    def get_all_etfs(self) -> List:
        """获取所有相关ETF"""
        from backend.market import CandidateETF
        etf_codes = self._engine.get_all_fund_codes()

        # 转换为 ETF 对象列表
        result = []
        for code in etf_codes:
            etf = self._config.get_etf_by_code(code)
            if etf:
                result.append(etf)
        return result

    def find_related_etfs_with_real_weight(self, stock_code: str) -> List[dict]:
        """
        查找股票相关的ETF（带真实权重验证）

        只返回持仓占比 >= 5% 的 ETF

        Args:
            stock_code: 股票代码

        Returns:
            相关ETF列表
        """
        eligible_funds = self._engine.get_eligible_funds(stock_code)

        return [
            {
                'etf_code': f.etf_code,
                'etf_name': f.etf_name,
                'weight': f.weight,
                'rank': f.rank,
                'in_top10': f.in_top10,
                'category': f.category
            }
            for f in eligible_funds
        ]

    def scan_all_stocks(self) -> List:
        """
        扫描所有自选股

        Returns:
            生成的信号列表
        """
        result = self._engine.scan_all()

        # 将生成的信号添加到历史记录
        for signal in result.signals:
            self._signal_history.append(signal)

        return result.signals

    def save_signals(self) -> None:
        """保存信号到持久化存储"""
        from backend.signal.repository import FileSignalRepository
        from backend.signal import SignalManager

        repo = FileSignalRepository("data/signals.json")
        manager = SignalManager(repository=repo)

        for signal in self._signal_history:
            manager.save_and_notify(signal)

    @property
    def stock_etf_mapping(self) -> dict:
        """获取股票-ETF映射关系"""
        return self._engine.get_security_fund_mapping()

    @property
    def config(self) -> Config:
        """获取配置"""
        return self._config


def create_monitor_with_defaults() -> LimitUpMonitor:
    """
    使用默认配置创建监控器实例

    Returns:
        LimitUpMonitor 实例
    """
    config = Config.load()

    # 创建各组件
    from backend.market.cn.quote_fetcher import CNQuoteFetcher
    from backend.market.cn.etf_holding_provider import CNETFHoldingProvider
    from backend.market.cn.etf_quote import CNETFQuoteFetcher

    quote_fetcher = CNQuoteFetcher()
    etf_holder_provider = CNETFHoldingProvider()
    etf_holdings_provider = CNETFHoldingProvider()
    etf_quote_provider = CNETFQuoteFetcher()

    # 创建引擎
    engine = ArbitrageEngineFactory.create_engine(
        quote_fetcher=quote_fetcher,
        etf_holder_provider=etf_holder_provider,
        etf_holdings_provider=etf_holdings_provider,
        etf_quote_provider=etf_quote_provider,
        config=config
    )

    return LimitUpMonitor(engine=engine, config=config)
