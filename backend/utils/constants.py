"""
常量定义模块
集中管理系统中使用的常量
"""

from typing import Tuple


# ==================== 策略相关常量 ====================

# ETF持仓权重阈值
DEFAULT_MIN_WEIGHT: float = 0.05  # 5%

# 时间相关（秒）
DEFAULT_MIN_TIME_TO_CLOSE: int = 1800  # 30分钟

# 成交额相关（万元）
DEFAULT_MIN_ETF_VOLUME: int = 5000  # 5000万元 = 5亿元


# ==================== 缓存相关常量 ====================

class CacheConfig:
    """缓存配置"""
    DEFAULT_TTL: int = 30  # 默认缓存过期时间（秒）
    DEFAULT_REFRESH_INTERVAL: int = 15  # 默认刷新间隔（秒）
