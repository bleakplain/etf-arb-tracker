"""
通用的数据解析器模块
提供统一的数据解析逻辑，消除代码重复
"""

import pandas as pd
from typing import Dict, Optional, Any
from datetime import datetime
from loguru import logger

from backend.data.utils import (
    safe_float,
    safe_int,
    is_limit_up,
    is_limit_down,
)
from backend.data.column_mappings import STANDARD_TO_INTERNAL


def parse_quote_row(
    row: pd.Series,
    asset_type: str = "stock"
) -> Optional[Dict]:
    """
    通用的行情行解析函数

    Args:
        row: DataFrame的一行数据
        asset_type: 资产类型 ('stock' 或 'etf')

    Returns:
        标准化的行情数据字典
    """
    try:
        # 使用标准列名映射获取内部字段
        code = str(row.get('代码', ''))
        name = str(row.get('名称', ''))
        price = safe_float(row.get('最新价'))
        prev_close = safe_float(row.get('昨收'))
        open_price = safe_float(row.get('今开'))
        high = safe_float(row.get('最高'))
        low = safe_float(row.get('最低'))
        volume = safe_int(row.get('成交量'))
        amount = safe_float(row.get('成交额'))
        change = safe_float(row.get('涨跌额', price - prev_close))
        change_pct = safe_float(row.get('涨跌幅'))

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
            'change': change,
            'change_pct': change_pct,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 添加涨跌停标记（仅股票）
        if asset_type == 'stock':
            result['is_limit_up'] = is_limit_up(code, change_pct)
            result['is_limit_down'] = is_limit_down(code, change_pct)

        # ETF特有字段
        if asset_type == 'etf':
            result['asset_type'] = 'ETF'
            result['iopv'] = 0.0
            result['premium'] = None

        # 添加其他可能存在的字段
        if '换手率' in row.index:
            result['turnover'] = safe_float(row.get('换手率'))
        if '市盈率' in row.index:
            result['pe'] = safe_float(row.get('市盈率'))
        if '市净率' in row.index:
            result['pb'] = safe_float(row.get('市净率'))
        if 'ts_code' in row.index:
            result['ts_code'] = str(row.get('ts_code', ''))

        return result

    except (ValueError, TypeError) as e:
        logger.error(f"解析行情数据失败: {e}, 行数据: {row.to_dict()}")
        return None


def add_limit_flags(df: pd.DataFrame, code_column: str = '代码') -> pd.DataFrame:
    """
    为DataFrame添加涨跌停标记

    Args:
        df: 行情DataFrame
        code_column: 股票代码列名

    Returns:
        添加了涨跌停标记的DataFrame
    """
    if '涨跌幅' in df.columns:
        df['is_limit_up'] = df.apply(
            lambda row: is_limit_up(row[code_column], row['涨跌幅']),
            axis=1
        )
        df['is_limit_down'] = df.apply(
            lambda row: is_limit_down(row[code_column], row['涨跌幅']),
            axis=1
        )
    return df


def normalize_api_response(
    data: Dict[str, Any],
    asset_type: str = "stock"
) -> Dict[str, Any]:
    """
    标准化API响应数据

    Args:
        data: 原始API响应数据
        asset_type: 资产类型

    Returns:
        标准化后的数据字典
    """
    # 处理price为0的情况
    price = data.get('price', 0)
    prev_close = data.get('prev_close', 0)

    if price == 0 and prev_close > 0:
        data['price'] = prev_close
        data['change'] = 0
        data['change_pct'] = 0

    # 确保时间戳存在
    if 'timestamp' not in data:
        data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return data


def batch_parse_quotes(
    df: pd.DataFrame,
    asset_type: str = "stock"
) -> Dict[str, Dict]:
    """
    批量解析行情DataFrame

    Args:
        df: 行情DataFrame
        asset_type: 资产类型

    Returns:
        {代码: 行情数据} 的字典
    """
    results = {}

    for _, row in df.iterrows():
        code = str(row.get('代码', ''))
        if not code:
            continue

        quote = parse_quote_row(row, asset_type)
        if quote:
            results[code] = quote

    return results
