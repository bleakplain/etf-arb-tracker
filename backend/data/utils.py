"""
共用工具函数模块
提供数据解析、股票代码转换等通用功能
"""

from typing import Union, Optional


def safe_float(value: Union[str, int, float, None], default: float = 0.0) -> float:
    """
    安全地转换为float

    Args:
        value: 待转换的值
        default: 默认值

    Returns:
        转换后的float值
    """
    try:
        if value is None or value == '' or value == '-':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Union[str, int, float, None], default: int = 0) -> int:
    """
    安全地转换为int

    Args:
        value: 待转换的值
        default: 默认值

    Returns:
        转换后的int值
    """
    try:
        if value is None or value == '' or value == '-':
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def is_limit_up(code: str, change_pct: float) -> bool:
    """
    判断是否涨停

    Args:
        code: 股票代码
        change_pct: 涨跌幅（小数形式，如0.0995表示9.95%）

    Returns:
        是否涨停
    """
    if change_pct < 0.095:
        return False

    # 科创板 (688xxx) 和 创业板 (300xxx, 301xxx) 涨停限制为 20%
    if code.startswith('688') or code.startswith('300') or code.startswith('301'):
        return change_pct >= 0.195
    # 北交所 (8xxxx, 4xxxx) 涨停限制为 30%
    elif code.startswith('8') or code.startswith('4'):
        return change_pct >= 0.295
    # 主板 涨停限制为 10%
    else:
        return change_pct >= 0.095


def is_limit_down(code: str, change_pct: float) -> bool:
    """
    判断是否跌停

    Args:
        code: 股票代码
        change_pct: 涨跌幅（小数形式，如-0.0995表示-9.95%）

    Returns:
        是否跌停
    """
    if change_pct > -0.095:
        return False

    # 科创板 (688xxx) 和 创业板 (300xxx, 301xxx) 跌停限制为 -20%
    if code.startswith('688') or code.startswith('300') or code.startswith('301'):
        return change_pct <= -0.195
    # 北交所 (8xxxx, 4xxxx) 跌停限制为 -30%
    elif code.startswith('8') or code.startswith('4'):
        return change_pct <= -0.295
    # 主板 跌停限制为 -10%
    else:
        return change_pct <= -0.095


def convert_code_format(code: str, format_type: str) -> str:
    """
    转换股票代码为指定格式

    Args:
        code: 6位股票代码
        format_type: 格式类型 ('tencent', 'tushare', 'standard')

    Returns:
        转换后的代码
    """
    if not code or len(code) != 6:
        return code

    if format_type == 'tushare':
        if '.' in code:
            return code
        if code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith(('0', '3', '8')):
            return f"{code}.SZ"
        return code

    # tencent 格式
    if format_type == 'tencent':
        if code.startswith('6'):
            return f'sh{code}'
        elif code.startswith(('0', '3')):
            return f'sz{code}'
        elif code.startswith('8') or code.startswith('4'):
            return f'bj{code}'
        return code

    # standard 格式返回纯数字
    if '.' in code:
        return code.split('.')[0]

    return code


def denormalize_code(ts_code: str) -> str:
    """
    将Tushare格式代码转换为标准格式

    Args:
        ts_code: Tushare格式代码，如 "600519.SH"

    Returns:
        标准格式代码，如 "600519"
    """
    return ts_code.split('.')[0] if '.' in ts_code else ts_code


def parse_price_data(
    code: str,
    name: str,
    price: float,
    prev_close: float,
    open_price: float = 0.0,
    high: float = 0.0,
    low: float = 0.0,
    volume: int = 0,
    amount: float = 0.0,
    change: Optional[float] = None,
    change_pct: Optional[float] = None,
    **kwargs
) -> dict:
    """
    解析并标准化股票价格数据

    Args:
        code: 股票代码
        name: 股票名称
        price: 最新价
        prev_close: 昨收价
        open_price: 今开价
        high: 最高价
        low: 最低价
        volume: 成交量（手）
        amount: 成交额（元）
        change: 涨跌额
        change_pct: 涨跌幅
        **kwargs: 其他字段

    Returns:
        标准化的行情数据字典
    """
    # 计算涨跌额和涨跌幅
    if change is None and prev_close > 0:
        change = price - prev_close
    if change_pct is None and prev_close > 0:
        change_pct = (change / prev_close) if change is not None else 0

    # 如果当前价为0（未开盘或停牌），使用昨收价代替
    if price == 0 and prev_close > 0:
        price = prev_close
        change = 0
        change_pct = 0

    result = {
        'code': code,
        'name': name,
        'price': price,
        'prev_close': prev_close,
        'open': open_price,
        'high': high,
        'low': low,
        'volume': volume,
        'amount': amount,
        'change': change if change is not None else 0,
        'change_pct': change_pct if change_pct is not None else 0,
        'is_limit_up': is_limit_up(code, change_pct if change_pct is not None else 0),
        'is_limit_down': is_limit_down(code, change_pct if change_pct is not None else 0),
    }

    # 添加额外字段
    result.update(kwargs)

    return result
