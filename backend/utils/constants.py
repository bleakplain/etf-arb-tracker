"""
常量定义模块
集中管理系统中使用的常量
"""

from typing import Tuple


# ==================== 通用策略相关常量 ====================

# ETF持仓权重阈值
DEFAULT_MIN_WEIGHT: float = 0.05  # 5%

# 时间相关（秒）
DEFAULT_MIN_TIME_TO_CLOSE: int = 1800  # 30分钟
HIGH_RISK_TIME_THRESHOLD: int = 1800  # 30分钟，高风险时间阈值

# 涨停相关
STRONG_LIMIT_SEAL_AMOUNT_THRESHOLD: int = 1_000_000  # 100万元，强势涨停封单金额阈值

# 成交额相关（万元）
DEFAULT_MIN_ETF_VOLUME: int = 5000  # 5000万元 = 5亿元


# ==================== A股市场特定常量 ====================

class CNMarketConstants:
    """A股市场常量"""

    # 涨停阈值（涨幅百分比）
    LIMIT_UP_THRESHOLD_MAIN_BOARD: float = 0.095  # 主板9.5%（接近10%涨停）
    LIMIT_UP_THRESHOLD_STAR_BOARD: float = 0.195  # 科创板/创业板19.5%（接近20%涨停）
    LIMIT_UP_THRESHOLD_BEIJING: float = 0.295  # 北交所29.5%（接近30%涨停）

    # 默认涨停检测阈值
    DEFAULT_LIMIT_UP_THRESHOLD: float = LIMIT_UP_THRESHOLD_MAIN_BOARD  # 默认使用主板阈值

    # 涨停验证阈值
    LIMIT_UP_VALID_THRESHOLD: float = 9.5  # 涨停验证时使用的阈值百分比

    # 最小持仓权重
    DEFAULT_MIN_WEIGHT: float = 0.05  # 5%

    # 时间相关
    DEFAULT_MIN_TIME_TO_CLOSE: int = 1800  # 距收盘最小时间（秒），30分钟

    # 成交额相关
    DEFAULT_MIN_DAILY_AMOUNT: int = 50_000_000  # 最小日成交额（元），5000万元


# ==================== 缓存相关常量 ====================

class CacheConfig:
    """缓存配置"""
    DEFAULT_TTL: int = 30  # 默认缓存过期时间（秒）
    DEFAULT_REFRESH_INTERVAL: int = 15  # 默认刷新间隔（秒）
