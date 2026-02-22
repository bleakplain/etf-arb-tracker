"""A股套利包

专门处理A股市场的涨停套利机会。
当股票涨停时，通过买入包含该股票的ETF来获取套利机会。
"""

from backend.arbitrage.cn.arbitrage_engine import ArbitrageEngineCN, ScanResult
from backend.arbitrage.config import ArbitrageEngineConfig

__all__ = [
    'ArbitrageEngineCN',
    'ScanResult',
    'ArbitrageEngineConfig',
]
