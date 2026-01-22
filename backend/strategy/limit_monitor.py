"""
涨停监控器 - 重构版

职责：
1. 协调各个组件完成监控流程
2. 管理监控状态
3. 提供简洁的API接口

采用依赖注入模式，所有依赖通过构造函数传入
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Optional
from loguru import logger
from dataclasses import dataclass

# 确保日志系统已初始化
try:
    from config import get
    get()  # 这会触发日志初始化
except Exception:
    pass  # 如果已初始化或配置加载失败，忽略

from backend.domain.interfaces import (
    IQuoteFetcher,
    IETFHolderProvider,
    IETFHoldingsProvider,
    IETFQuoteProvider,
    ISignalEvaluator,
    ISignalSender
)
from backend.domain.value_objects import TradingSignal, StockInfo
from backend.domain.models import LimitUpInfo

from backend.strategy.limit_checker import LimitChecker
from backend.strategy.etf_selector import ETFSelector
from backend.strategy.signal_generator import SignalGenerator
from backend.strategy.signal_repository import FileSignalRepository
from backend.strategy.signal_evaluators import SignalEvaluatorFactory

from config import Config


@dataclass
class StockConfig:
    """股票配置"""
    code: str
    name: str
    market: str
    notes: str = ""


class LimitUpMonitor:
    """
    涨停监控器 - 重构版

    职责单一化：协调各组件完成监控任务

    架构：
    - LimitChecker: 检查涨停状态
    - ETFSelector: 选择合适的ETF
    - SignalGenerator: 生成交易信号
    - SignalRepository: 管理信号存储
    - SignalSender: 发送信号通知
    """

    def __init__(
        self,
        quote_fetcher: IQuoteFetcher,
        etf_holder_provider: IETFHolderProvider,
        etf_holdings_provider: IETFHoldingsProvider,
        etf_quote_provider: IETFQuoteProvider,
        watch_stocks: List[StockConfig],
        config: Config = None,
        evaluator_type: str = "default"
    ):
        """
        初始化监控器

        Args:
            quote_fetcher: 行情数据获取器
            etf_holder_provider: ETF持仓关系提供者
            etf_holdings_provider: ETF持仓详情提供者
            etf_quote_provider: ETF行情提供者
            watch_stocks: 监控的股票列表
            config: 应用配置
            evaluator_type: 信号评估器类型
        """
        self.config = config or Config.load()
        self.watch_stocks = watch_stocks

        # 创建信号评估器
        self.signal_evaluator = SignalEvaluatorFactory.create(
            evaluator_type,
            self.config.signal_evaluation
        )

        # 初始化各个组件（依赖注入）
        self._limit_checker = LimitChecker(quote_fetcher)

        self._etf_selector = ETFSelector(
            etf_holder_provider,
            etf_holdings_provider,
            min_weight=self.config.strategy.min_weight
        )

        self._signal_generator = SignalGenerator(
            quote_fetcher,
            etf_quote_provider,
            self.signal_evaluator,
            min_time_to_close=self.config.strategy.min_time_to_close,
            min_etf_volume=self.config.strategy.min_etf_volume * 10000
        )

        self._signal_repository = FileSignalRepository()

        # 加载ETF映射
        self._load_or_build_mapping()

        logger.info("涨停监控器初始化完成")
        logger.info(f"监控股票数量: {len(self.watch_stocks)}")
        logger.info(f"覆盖ETF数量: {len(self.get_all_etfs())}")

    def _load_or_build_mapping(self) -> None:
        """加载或构建股票-ETF映射"""
        mapping_file = "data/stock_etf_mapping.json"

        # 尝试加载已有映射
        self._etf_selector.load_mapping(mapping_file)

        if self._etf_selector._mapping:
            logger.info("使用已有映射关系")
        else:
            logger.info("未找到已有映射，开始构建...")
            stock_codes = [s.code for s in self.watch_stocks]
            etf_codes = [e.code for e in self.config.watch_etfs]
            self._etf_selector.build_mapping(stock_codes, etf_codes)
            self._etf_selector.save_mapping(mapping_file)

    @property
    def stock_etf_mapping(self) -> dict:
        """获取股票-ETF映射关系"""
        return self._etf_selector._mapping

    @property
    def stock_fetcher(self):
        """获取行情获取器（兼容旧代码）"""
        return self._limit_checker._quote_fetcher

    @property
    def etf_fetcher(self):
        """获取ETF行情获取器（兼容旧代码）"""
        return self._signal_generator._etf_quote_provider

    @property
    def holder_fetcher(self):
        """获取持仓关系提供者（兼容旧代码）"""
        return self._etf_selector._holder_provider

    @property
    def holdings_fetcher(self):
        """获取持仓详情提供者（兼容旧代码）"""
        return self._etf_selector._holdings_provider

    def get_all_etfs(self) -> List[str]:
        """获取所有相关ETF代码"""
        return self._etf_selector.get_all_etf_codes()

    @staticmethod
    def normalize_stock_code(stock_code: str) -> str:
        """
        标准化股票代码，去掉市场前缀

        Args:
            stock_code: 股票代码，可能带前缀如 sh688319, sz000001

        Returns:
            纯数字股票代码，如 688319, 000001
        """
        prefixes = ['sh', 'sz', 'bj']
        code = stock_code.lower()
        for prefix in prefixes:
            if code.startswith(prefix):
                return code[2:]
        return stock_code

    def find_related_etfs(self, stock_code: str) -> List[dict]:
        """
        找到与股票相关的ETF（用于API展示）

        Returns:
            [{etf_code, etf_name, weight, category}, ...]
        """
        normalized_code = self.normalize_stock_code(stock_code)
        return self._etf_selector.find_related_etfs(normalized_code)

    def find_related_etfs_with_real_weight(self, stock_code: str) -> List[dict]:
        """
        找到与股票相关的ETF，并获取真实持仓权重

        策略要求：股票在ETF中的持仓占比必须 >= 5%

        Returns:
            [{etf_code, etf_name, weight, rank, in_top10, top10_ratio}, ...]
        """
        normalized_code = self.normalize_stock_code(stock_code)
        etf_refs = self._etf_selector.find_eligible_etfs(normalized_code)

        return [
            {
                'etf_code': e.etf_code,
                'etf_name': e.etf_name,
                'category': e.category.value,
                'weight': e.weight,
                'rank': e.rank,
                'in_top10': e.in_top10,
                'top10_ratio': e.top10_ratio
            }
            for e in etf_refs
        ]

    def get_stock_weight_in_etf(self, stock_code: str, etf_code: str) -> dict:
        """
        获取股票在ETF中的实际权重和排名

        Returns:
            {
                'weight': float,
                'rank': int,
                'in_top10': bool,
                'top10_ratio': float
            }
        """
        return self._etf_selector._get_stock_weight(stock_code, etf_code)

    def check_limit_up(self, stock_code: str) -> Optional[dict]:
        """
        检查单只股票是否涨停

        Returns:
            涨停信息字典，如果未涨停返回None
        """
        limit_info = self._limit_checker.check_limit_up(stock_code)
        return limit_info.to_dict() if limit_info else None

    def evaluate_signal_quality(self, limit_info: dict, etf_info: dict) -> tuple:
        """
        评估信号质量

        Args:
            limit_info: 涨停股票信息
            etf_info: ETF信息

        Returns:
            (confidence, risk_level) - (置信度, 风险等级)
        """
        return self.signal_evaluator.evaluate(limit_info, etf_info)

    def generate_signal(self, stock_code: str) -> Optional[TradingSignal]:
        """
        生成交易信号

        套利策略：
        1. 检查股票是否涨停
        2. 查找该股票持仓占比>=min_weight的ETF
        3. 选择权重最高的ETF
        4. 验证时间、流动性等条件
        5. 生成买入信号
        """
        # 1. 检查是否涨停
        limit_info = self._limit_checker.check_limit_up(stock_code)
        if not limit_info:
            return None

        # 2. 获取符合条件ETF列表
        eligible_etfs = self._etf_selector.find_eligible_etfs(stock_code)
        if not eligible_etfs:
            return None

        # 3. 生成信号
        signal = self._signal_generator.generate_signal(limit_info, eligible_etfs)
        if not signal:
            return None

        # 4. 标记已处理
        self._limit_checker.mark_processed(stock_code)

        return signal

    def scan_all_stocks(self) -> List[TradingSignal]:
        """
        扫描所有自选股，生成信号

        Returns:
            本次扫描生成的信号列表
        """
        signals = []

        logger.info(f"开始扫描 {len(self.watch_stocks)} 只自选股...")

        for stock in self.watch_stocks:
            try:
                signal = self.generate_signal(stock.code)
                if signal:
                    signals.append(signal)
                    self._signal_repository.save(signal)

                time.sleep(0.1)  # 避免请求过快

            except Exception as e:
                logger.error(f"扫描股票 {stock.code} 失败: {e}")

        logger.info(f"扫描完成，生成 {len(signals)} 个信号")

        return signals

    def run_once(self) -> List[TradingSignal]:
        """执行一次监控扫描"""
        logger.info("=" * 50)
        logger.info(f"执行监控扫描 - {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 检查是否交易时间
        if not self._limit_checker._quote_fetcher.is_trading_time():
            logger.info("当前不在交易时间")
            return []

        return self.scan_all_stocks()

    def run_loop(self, interval: int = 60):
        """
        持续运行监控

        Args:
            interval: 扫描间隔（秒）
        """
        logger.info(f"开始持续监控，扫描间隔: {interval}秒")

        try:
            while True:
                try:
                    signals = self.run_once()
                    logger.info(f"本次扫描生成 {len(signals)} 个信号")

                    # 等待下一次扫描
                    time.sleep(interval)

                except KeyboardInterrupt:
                    logger.info("收到停止信号，退出监控")
                    break
                except Exception as e:
                    logger.error(f"监控循环出错: {e}")
                    time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("监控已停止")

    def save_signals(self, filepath: str = "data/signals.json"):
        """保存信号历史到文件"""
        # 兼容旧接口，实际信号已在生成时保存
        logger.info(f"信号已自动保存到 {filepath}")

    @property
    def signal_history(self) -> List[TradingSignal]:
        """获取信号历史"""
        return self._signal_repository.get_all_signals()

    def send_notification(self, signal: TradingSignal, sender: ISignalSender) -> bool:
        """
        发送信号通知

        Args:
            signal: 交易信号
            sender: 信号发送器

        Returns:
            是否发送成功
        """
        try:
            logger.info(f"📢 信号通知: {signal.stock_name} -> {signal.etf_name}")
            return sender.send_signal(signal)
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            return False


# ============ 兼容旧接口的工厂函数 ============

def create_monitor_with_defaults(config: Config = None, evaluator_type: str = "default") -> LimitUpMonitor:
    """
    使用默认实现创建监控器（兼容旧代码）

    Args:
        config: 应用配置
        evaluator_type: 信号评估器类型

    Returns:
        配置好的监控器实例
    """
    config = config or Config.load()

    from backend.data.stock_quote import StockQuoteFetcher
    from backend.data.etf_quote import ETFQuoteFetcher
    from backend.data.etf_holder import ETFHolderFetcher
    from backend.data.etf_holdings import ETFHoldingsFetcher

    # 获取自选股代码列表
    watch_codes = [s.code for s in config.my_stocks] if config.my_stocks else []

    return LimitUpMonitor(
        quote_fetcher=StockQuoteFetcher(watch_stocks=watch_codes),
        etf_holder_provider=ETFHolderFetcher(),
        etf_holdings_provider=ETFHoldingsFetcher(),
        etf_quote_provider=ETFQuoteFetcher(),
        watch_stocks=config.my_stocks,
        config=config,
        evaluator_type=evaluator_type
    )


# ============ 主函数 ============

def main():
    """主函数（兼容旧接口）"""

    # 创建监控器
    monitor = create_monitor_with_defaults()

    # 先执行一次扫描
    signals = monitor.run_once()

    if signals:
        for signal in signals:
            print("\n" + "=" * 60)
            print(f"📈 涨停ETF套利信号")
            print("=" * 60)
            print(f"时间: {signal.timestamp}")
            print(f"\n【涨停股票】")
            print(f"  代码: {signal.stock_code}")
            print(f"  名称: {signal.stock_name}")
            print(f"  价格: ¥{signal.stock_price:.2f}")
            print(f"  涨幅: +{signal.change_pct:.2f}%")
            print(f"\n【建议操作】")
            print(f"  买入ETF: {signal.etf_name} ({signal.etf_code})")
            print(f"  当前价格: ¥{signal.etf_price:.3f}")
            print(f"  持仓占比: {signal.actual_weight*100:.2f}% ✓ (≥5%)")
            print(f"  持仓排名: 第{signal.weight_rank}名")
            print(f"  前10占比: {signal.top10_ratio*100:.1f}%")
            print(f"  溢价率: {signal.etf_premium:+.2f}%")
            print(f"\n【信号评估】")
            print(f"  置信度: {signal.confidence}")
            print(f"  风险等级: {signal.risk_level}")
            print(f"  说明: {signal.reason}")
            print("=" * 60)

    # 如果是交易时间，询问是否持续监控
    if monitor.stock_fetcher.is_trading_time():
        print("\n当前为交易时间，是否启动持续监控？(y/n): ", end="")
        print("演示模式，不启动持续监控")


if __name__ == "__main__":
    main()
