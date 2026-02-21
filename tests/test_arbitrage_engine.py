"""
ArbitrageEngine 单元测试

测试套利引擎的核心功能：
1. 策略执行器
2. 套利引擎
3. 策略链配置
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from backend.engine.arbitrage_engine import ArbitrageEngine, ScanResult
from backend.engine.strategy_executor import StrategyExecutor
from backend.strategies.event_detectors import LimitUpDetector
from backend.strategies.fund_selectors import HighestWeightSelector
from backend.strategies.signal_filters import TimeFilter


class MockQuoteFetcher:
    """模拟行情获取器"""

    def __init__(self):
        self._quotes = {
            '600519': {
                'code': '600519',
                'name': '贵州茅台',
                'price': 1800.0,
                'change_pct': 0.1001,  # 10.01%
                'is_limit_up': True,
                'timestamp': '14:00:00',
                'volume': 1000000,
                'amount': 1800000000
            },
            '300750': {
                'code': '300750',
                'name': '宁德时代',
                'price': 256.80,
                'change_pct': 0.2001,  # 20.01%
                'is_limit_up': True,
                'timestamp': '13:30:00',
                'volume': 5000000,
                'amount': 1284000000
            }
        }

    def get_stock_quote(self, code: str):
        return self._quotes.get(code)

    def get_batch_quotes(self, codes):
        return {c: self._quotes.get(c) for c in codes}

    def is_trading_time(self):
        return True

    def get_time_to_close(self):
        return 3600  # 距收盘1小时


class MockETFHolderProvider:
    """模拟ETF持仓关系提供者"""

    def __init__(self):
        self._mapping = {
            '600519': [
                {'etf_code': '510300', 'etf_name': '沪深300ETF'},
                {'etf_code': '510500', 'etf_name': '中证500ETF'},
            ],
            '300750': [
                {'etf_code': '516160', 'etf_name': '新能源车ETF'},
            ]
        }

    def load_mapping(self, filepath):
        return self._mapping

    def save_mapping(self, mapping, filepath):
        pass

    def build_stock_etf_mapping(self, stock_codes, etf_codes):
        return self._mapping


class MockETFHoldingsProvider:
    """模拟ETF持仓详情提供者"""

    def get_etf_top_holdings(self, etf_code):
        holdings_map = {
            '510300': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.08},
                {'stock_code': '600036', 'stock_name': '招商银行', 'weight': 0.05},
            ],
            '510500': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.04},
            ],
            '516160': [
                {'stock_code': '300750', 'stock_name': '宁德时代', 'weight': 0.085},
            ]
        }

        return {
            'etf_code': etf_code,
            'etf_name': '510300' if etf_code == '510300' else 'Other',
            'top_holdings': holdings_map.get(etf_code, []),
            'total_weight': 0.13
        }


class MockETFQuoteProvider:
    """模拟ETF行情提供者"""

    def get_etf_quote(self, code):
        return {
            'code': code,
            'name': 'Test ETF',
            'price': 1.234,
            'premium': 2.5
        }

    def get_etf_batch_quotes(self, codes):
        return {c: self.get_etf_quote(c) for c in codes}

    def check_liquidity(self, code, min_amount):
        return True


def test_strategy_executor():
    """测试策略执行器"""
    print("\n=== 测试策略执行器 ===")

    # 创建策略组件
    detector = LimitUpDetector(min_change_pct=0.095)
    selector = HighestWeightSelector(min_weight=0.05)
    filters = [TimeFilter(min_time_to_close=1800)]

    # 创建执行器
    executor = StrategyExecutor(detector, selector, filters)

    # 测试数据
    quote = {
        'code': '600519',
        'name': '贵州茅台',
        'price': 1800.0,
        'change_pct': 0.10,
        'is_limit_up': True,
        'timestamp': '14:00:00'
    }

    from backend.domain.value_objects import ETFReference

    eligible_funds = [
        ETFReference(
            etf_code='510300',
            etf_name='沪深300ETF',
            weight=0.08,
            category='broad_index',
            rank=3,
            in_top10=True,
            top10_ratio=0.65
        )
    ]

    # 执行策略
    signal, logs = executor.execute(
        quote=quote,
        eligible_funds=eligible_funds,
        etf_quote_provider=MockETFQuoteProvider(),
        signal_evaluator=None
    )

    print(f"策略信息: {executor.strategy_info}")
    print(f"信号生成: {'成功' if signal else '失败'}")
    for log in logs:
        print(f"  {log}")

    if signal:
        print(f"信号ID: {signal.signal_id}")
        print(f"理由: {signal.reason}")

    assert signal is not None, "应该生成信号"
    print("✓ 策略执行器测试通过")


def test_arbitrage_engine():
    """测试套利引擎"""
    print("\n=== 测试套利引擎 ===")

    # 创建引擎
    engine = ArbitrageEngine(
        quote_fetcher=MockQuoteFetcher(),
        etf_holder_provider=MockETFHolderProvider(),
        etf_holdings_provider=MockETFHoldingsProvider(),
        etf_quote_provider=MockETFQuoteProvider(),
        watch_securities=['600519', '300750'],
        signal_evaluator=None,
        config=None
    )

    # 获取策略信息
    strategy_info = engine.get_strategy_info()
    print(f"策略配置: {strategy_info}")

    # 扫描单个证券
    signal = engine.scan_security('600519')
    print(f"扫描600519: {'成功' if signal else '无信号'}")

    # 扫描所有证券
    result = engine.scan_all()
    print(f"扫描结果: {result.to_dict()}")

    assert result.total_scanned == 2, "应该扫描2只证券"
    assert len(result.signals) >= 1, "至少生成1个信号"

    print("✓ 套利引擎测试通过")


if __name__ == "__main__":
    print("开始测试...")
    print("=" * 60)

    try:
        test_strategy_executor()
        test_arbitrage_engine()
        print("\n" + "=" * 60)
        print("所有测试通过! ✓")
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
