"""
股票代码工具函数
提供股票代码标准化等通用功能
"""

from typing import Set


# 市场前缀常量
MARKET_PREFIXES: Set[str] = {'sh', 'sz', 'bj'}


def normalize_stock_code(stock_code: str) -> str:
    """
    标准化股票代码，去掉市场前缀

    Args:
        stock_code: 股票代码，可能带前缀如 sh688319, sz000001

    Returns:
        纯数字股票代码，如 688319, 000001

    Examples:
        >>> normalize_stock_code("sh600519")
        "600519"
        >>> normalize_stock_code("SZ000001")
        "000001"
        >>> normalize_stock_code("600519")
        "600519"
    """
    code = stock_code.lower()
    for prefix in MARKET_PREFIXES:
        if code.startswith(prefix):
            return code[2:]
    return stock_code


def add_market_prefix(stock_code: str, market: str) -> str:
    """
    为股票代码添加市场前缀

    Args:
        stock_code: 纯数字股票代码
        market: 市场代码 ('sh', 'sz', 'bj')

    Returns:
        带前缀的股票代码

    Examples:
        >>> add_market_prefix("600519", "sh")
        "sh600519"
    """
    market = market.lower()
    if market in MARKET_PREFIXES:
        return f"{market}{stock_code}"
    return stock_code
