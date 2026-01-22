"""
统一的列名映射模块
为不同数据源提供统一的列名转换
"""

from typing import Dict, Any
from enum import Enum


class StandardColumns(Enum):
    """标准列名枚举"""
    CODE = "代码"
    NAME = "名称"
    PRICE = "最新价"
    PREV_CLOSE = "昨收"
    OPEN = "今开"
    HIGH = "最高"
    LOW = "最低"
    VOLUME = "成交量"
    AMOUNT = "成交额"
    CHANGE = "涨跌额"
    CHANGE_PCT = "涨跌幅"
    TURNOVER = "换手率"
    TIMESTAMP = "时间戳"


# 标准中文列名到内部字段的映射
STANDARD_TO_INTERNAL: Dict[str, str] = {
    "代码": "code",
    "名称": "name",
    "最新价": "price",
    "昨收": "prev_close",
    "今开": "open",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
    "涨跌额": "change",
    "涨跌幅": "change_pct",
    "换手率": "turnover",
    "时间戳": "timestamp",
    "市盈率": "pe",
    "市净率": "pb",
    "ts_code": "ts_code",
}


# 腾讯数据源列名映射
TENCENT_COLUMN_MAPPING: Dict[str, str] = {
    'code': '代码',
    'name': '名称',
    'price': '最新价',
    'prev_close': '昨收',
    'open': '今开',
    'high': '最高',
    'low': '最低',
    'volume': '成交量',
    'amount': '成交额',
    'change': '涨跌额',
    'change_pct': '涨跌幅',
}


# Tushare数据源列名映射
TUSHARE_COLUMN_MAPPING: Dict[str, str] = {
    'ts_code': 'ts_code',
    'open': '今开',
    'high': '最高',
    'low': '最低',
    'close': '最新价',
    'pre_close': '昨收',
    'vol': '成交量',
    'amount': '成交额',
    'pct_chg': '涨跌幅',
    'turnover_rate': '换手率',
    'pe': '市盈率',
    'pb': '市净率',
}


# 内部字段到标准中文列名的反向映射
INTERNAL_TO_STANDARD: Dict[str, str] = {
    v: k for k, v in STANDARD_TO_INTERNAL.items()
}


def get_column_mapping(source_name: str) -> Dict[str, str]:
    """
    获取指定数据源的列名映射

    Args:
        source_name: 数据源名称 ('tencent', 'tushare', 'eastmoney')

    Returns:
        列名映射字典 {内部字段: 标准中文列名}
    """
    mappings = {
        'tencent': TENCENT_COLUMN_MAPPING,
        'tushare': TUSHARE_COLUMN_MAPPING,
    }
    return mappings.get(source_name, {})


def to_standard_columns(df_columns: Any, source_name: str) -> Dict[str, str]:
    """
    生成从DataFrame列名到标准中文列名的映射

    Args:
        df_columns: DataFrame的列名或列名列表
        source_name: 数据源名称

    Returns:
        {原列名: 标准中文列名} 的映射
    """
    source_mapping = get_column_mapping(source_name)
    return source_mapping


def standardize_dict(data: Dict[str, Any], source_name: str) -> Dict[str, Any]:
    """
    将数据源返回的字典转换为标准格式

    Args:
        data: 数据源返回的原始字典
        source_name: 数据源名称

    Returns:
        标准化后的字典（使用标准中文列名）
    """
    source_mapping = get_column_mapping(source_name)
    return {source_mapping.get(k, k): v for k, v in data.items()}
