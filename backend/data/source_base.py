"""
数据源基础架构
支持免费高频和付费低频相结合的多数据源策略
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any, Set
from datetime import datetime
import threading


# 评分算法配置
class ScoringConfig:
    """数据源评分算法配置"""

    # 评分权重
    SUCCESS_RATE_WEIGHT = 0.5      # 成功率权重
    SPEED_SCORE_WEIGHT = 0.3        # 速度评分权重
    PRIORITY_SCORE_WEIGHT = 0.2     # 优先级评分权重

    # 速度评分参数
    SPEED_FULL_MARK_SECONDS = 1.0   # 满分速度（秒）
    SPEED_ZERO_MARK_SECONDS = 5.0   # 零分速度（秒）

    # 优先级评分参数
    PRIORITY_MAX_VALUE = 100        # 最大优先级值

    # 类型加分
    FREE_HIGH_FREQ_BONUS = 0.2      # 免费高频数据源加分

    # 状态判断参数
    CONSECUTIVE_FAILURES_FOR_FAILED = 3   # 连续失败次数达到此值标记为FAILED
    CONSECUTIVE_FAILURES_FOR_DEGRADED = 1 # 连续失败次数达到此值标记为DEGRADED

    # 重试参数
    DEFAULT_MIN_RETRY_INTERVAL = 30  # 默认最小重试间隔（秒）


class SourceType(Enum):
    """数据源类型"""
    FREE_HIGH_FREQ = "free_high_freq"
    FREE_LOW_FREQ = "free_low_freq"
    PAID_HIGH_FREQ = "paid_high_freq"
    PAID_LOW_FREQ = "paid_low_freq"
    FALLBACK = "fallback"


class DataSourceStatus(Enum):
    """数据源状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"


class DataType(Enum):
    """数据类型"""
    STOCK_REALTIME = "stock_realtime"
    ETF_REALTIME = "etf_realtime"
    STOCK_HISTORY = "stock_history"
    FINANCIAL = "financial"
    INDEX = "index"
    FUND = "fund"


@dataclass
class SourceCapability:
    """数据源能力描述"""
    supported_types: Set[DataType]         # 支持的数据类型
    realtime: bool                         # 是否支持实时数据
    historical: bool                       # 是否支持历史数据
    batch_query: bool                      # 是否支持批量查询
    max_batch_size: int = 0                # 批量查询最大数量（0表示无限制）
    requires_token: bool = False           # 是否需要token
    rate_limit: int = 0                    # 每分钟请求限制（0表示无限制）


@dataclass
class SourceMetrics:
    """数据源性能指标"""
    name: str
    source_type: SourceType
    status: DataSourceStatus = DataSourceStatus.HEALTHY
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_time: float = 0.0
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    consecutive_failures: int = 0
    last_attempt_time: Optional[datetime] = None
    min_retry_interval: int = 30
    rate_limit_reset_time: Optional[datetime] = None
    rate_limit_remaining: int = 0

    def record_success(self, elapsed: float):
        """记录成功请求"""
        self.request_count += 1
        self.success_count += 1
        self.total_time += elapsed
        self.last_success_time = datetime.now()
        self.consecutive_failures = 0
        self._update_status()

    def record_failure(self):
        """记录失败请求"""
        self.request_count += 1
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self.last_attempt_time = datetime.now()
        self.consecutive_failures += 1
        self._update_status()

    def should_retry_now(self) -> bool:
        """判断是否应该立即重试"""
        if self.last_attempt_time is None:
            return True

        elapsed = (datetime.now() - self.last_attempt_time).total_seconds()
        return elapsed >= self.min_retry_interval

    def get_avg_time(self) -> float:
        """获取平均响应时间"""
        if self.success_count == 0:
            return float('inf')
        return self.total_time / self.success_count

    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.request_count == 0:
            return 1.0
        return self.success_count / self.request_count

    def is_available(self) -> bool:
        """判断数据源是否可用"""
        return self.status not in [DataSourceStatus.FAILED, DataSourceStatus.DISABLED]

    def _update_status(self):
        """更新数据源状态"""
        if self.consecutive_failures >= ScoringConfig.CONSECUTIVE_FAILURES_FOR_FAILED:
            self.status = DataSourceStatus.FAILED
        elif self.consecutive_failures >= ScoringConfig.CONSECUTIVE_FAILURES_FOR_DEGRADED or self.failure_count > self.success_count:
            self.status = DataSourceStatus.DEGRADED
        else:
            self.status = DataSourceStatus.HEALTHY

    def __repr__(self):
        return (f"SourceMetrics({self.name}, "
                f"type={self.source_type.value}, "
                f"status={self.status.value}, "
                f"success_rate={self.get_success_rate():.1%}, "
                f"avg_time={self.get_avg_time():.2f}s)")


class BaseDataSource(ABC):
    """数据源基类"""

    def __init__(self, name: str, source_type: SourceType, priority: int = 0):
        self.name = name
        self.source_type = source_type
        self.priority = priority
        self.metrics = SourceMetrics(name=name, source_type=source_type)
        self.capability = self._get_capability()
        self._lock = threading.Lock()

    @abstractmethod
    def _get_capability(self) -> SourceCapability:
        """定义数据源能力"""

    @abstractmethod
    def _check_config(self) -> bool:
        """检查配置是否完整"""

    def is_configured(self) -> bool:
        """检查数据源是否已配置"""
        return self._check_config()

    def is_available(self) -> bool:
        """判断数据源是否可用"""
        return self.metrics.is_available() and self.is_configured()

    def supports(self, data_type: DataType) -> bool:
        """判断是否支持某种数据类型"""
        return data_type in self.capability.supported_types

    def get_score(self, data_type: DataType) -> float:
        """
        获取数据源评分（用于排序）
        考虑因素：优先级、成功率、速度、数据类型匹配
        使用 ScoringConfig 中的配置参数
        """
        if not self.is_available() or not self.supports(data_type):
            return -1.0

        success_rate = self.metrics.get_success_rate()
        avg_time = self.metrics.get_avg_time()

        # 速度评分（使用配置参数）
        speed_range = ScoringConfig.SPEED_ZERO_MARK_SECONDS - ScoringConfig.SPEED_FULL_MARK_SECONDS
        speed_score = max(0, 1 - (avg_time - ScoringConfig.SPEED_FULL_MARK_SECONDS) / speed_range)

        # 优先级评分（使用配置参数）
        priority_score = max(0, 1 - self.priority / ScoringConfig.PRIORITY_MAX_VALUE)

        # 类型匹配加分（使用配置参数）
        type_bonus = ScoringConfig.FREE_HIGH_FREQ_BONUS if self.source_type == SourceType.FREE_HIGH_FREQ else 0

        # 综合评分（使用配置权重）
        return (
            success_rate * ScoringConfig.SUCCESS_RATE_WEIGHT +
            speed_score * ScoringConfig.SPEED_SCORE_WEIGHT +
            priority_score * ScoringConfig.PRIORITY_SCORE_WEIGHT +
            type_bonus
        )

    def reset_metrics(self):
        """重置指标"""
        self.metrics = SourceMetrics(name=self.name, source_type=self.source_type)

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name}, type={self.source_type.value})"


@dataclass
class QueryContext:
    """查询上下文"""
    data_type: DataType
    force_refresh: bool = False
    timeout: int = 30
    fallback_on_error: bool = True
    max_retries: int = 3


@dataclass
class QueryResult:
    """查询结果"""
    data: Any
    source: str
    source_type: SourceType
    cached: bool = False
    elapsed: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
