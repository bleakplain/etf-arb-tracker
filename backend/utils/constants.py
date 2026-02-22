"""
常量定义模块
集中管理系统中使用的魔法数字
"""

from typing import Tuple


# ==================== 策略相关常量 ====================

# ETF持仓权重阈值
DEFAULT_MIN_WEIGHT: float = 0.05  # 5%
MIN_WEIGHT_THRESHOLD: float = 0.01  # 1%

# 时间相关（秒）
DEFAULT_MIN_TIME_TO_CLOSE: int = 1800  # 30分钟
MIN_SCAN_INTERVAL: int = 60  # 1分钟
MAX_SCAN_INTERVAL: int = 300  # 5分钟

# 成交额相关（万元）
DEFAULT_MIN_ETF_VOLUME: int = 5000  # 5000万元 = 5亿元
MIN_ETF_VOLUME_THRESHOLD: int = 1000  # 1000万元


# ==================== 缓存相关常量 ====================

class CacheConfig:
    """缓存配置"""
    DEFAULT_TTL: int = 30  # 默认缓存过期时间（秒）
    DEFAULT_REFRESH_INTERVAL: int = 15  # 默认刷新间隔（秒）
    SHUTDOWN_TIMEOUT: int = 2  # 线程关闭超时（秒）
    BACKEND_CACHE_TTL: int = 60  # 后端缓存有效期
    BACKEND_REFRESH_INTERVAL: int = 30  # 后端刷新间隔
    FRONTEND_REFRESH_INTERVAL: int = 10  # 前端刷新间隔


# ==================== 数据源相关常量 ====================

class DataSourceLimits:
    """数据源限制"""
    TENCENT_BATCH_SIZE: int = 100  # 腾讯API批量大小
    DEFAULT_REQUEST_INTERVAL: int = 5  # 默认请求间隔（秒）
    MIN_REQUEST_INTERVAL: int = 1  # 最小请求间隔（秒）


# ==================== API相关常量 ====================

class APIConfig:
    """API配置"""
    DEFAULT_PORT: int = 8000
    MAX_BACKTEST_SPAN_DAYS: int = 3650  # 最大回测时间跨度（10年）
    MIN_DATE_YEAR: int = 2000
    MAX_DATE_YEAR: int = 2099


# ==================== 回测相关常量 ====================

class BacktestConfig:
    """回测配置"""
    MAX_JOBS_IN_MEMORY: int = 100  # 内存中最多保留的回测任务数
    DEFAULT_PROGRESS_REPORT_INTERVAL: float = 0.1  # 进度报告间隔（10%）


# ==================== ETF持仓相关常量 ====================

class ETFHoldingConfig:
    """ETF持仓配置"""
    TOP10_THRESHOLD: int = 10  # 前10大持仓
    DEFAULT_MAX_POSITIONS: int = 5  # 默认最大持仓数


# ==================== 风控相关常量 ====================

class RiskControl:
    """风控配置"""
    DEFAULT_MAX_BUY_AMOUNT: int = 50  # 单次最大买入金额（万元）
    DEFAULT_TAKE_PROFIT: float = 3.0  # 止盈点（%）
    DEFAULT_STOP_LOSS: float = -2.0  # 止损点（%）
    DEFAULT_MAX_HOLD_DAYS: int = 3  # 持仓天数上限


# ==================== 信号评估相关常量 ====================

class SignalEvaluation:
    """信号评估配置"""
    # 置信度阈值
    CONFIDENCE_HIGH_WEIGHT: float = 0.10  # 10%
    CONFIDENCE_LOW_WEIGHT: float = 0.05  # 5%
    CONFIDENCE_HIGH_RANK: int = 3
    CONFIDENCE_LOW_RANK: int = 10

    # 风险评估阈值
    RISK_HIGH_TIME_SECONDS: int = 600  # 10分钟
    RISK_LOW_TIME_SECONDS: int = 3600  # 1小时
    RISK_TOP10_RATIO_HIGH: float = 0.70  # 70%
    RISK_MORNING_HOUR: int = 10  # 10点前
