"""
数据源基础架构
支持免费高频和付费低频相结合的多数据源策略
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from loguru import logger
import time
import threading


class SourceType(Enum):
    """数据源类型"""
    FREE_HIGH_FREQ = "free_high_freq"      # 免费高频（实时行情）
    FREE_LOW_FREQ = "free_low_freq"        # 免费低频（历史数据）
    PAID_HIGH_FREQ = "paid_high_freq"      # 付费高频
    PAID_LOW_FREQ = "paid_low_freq"        # 付费低频（财务、基本面等）
    FALLBACK = "fallback"                  # 兜底数据源


class DataSourceStatus(Enum):
    """数据源状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"                   # 未配置或被禁用


class DataType(Enum):
    """数据类型"""
    STOCK_REALTIME = "stock_realtime"      # 股票实时行情
    ETF_REALTIME = "etf_realtime"          # ETF实时行情
    STOCK_HISTORY = "stock_history"        # 股票历史数据
    FINANCIAL = "financial"                # 财务数据
    INDEX = "index"                        # 指数数据
    FUND = "fund"                          # 基金数据


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
    min_retry_interval: int = 30           # 最小重试间隔（秒）
    rate_limit_reset_time: Optional[datetime] = None
    rate_limit_remaining: int = 0          # 剩余配额

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

        elapsed_since_last_attempt = (datetime.now() - self.last_attempt_time).total_seconds()
        return elapsed_since_last_attempt >= self.min_retry_interval

    def check_rate_limit(self) -> bool:
        """检查是否超过速率限制"""
        if self.rate_limit_remaining <= 0:
            if self.rate_limit_reset_time and datetime.now() < self.rate_limit_reset_time:
                return False
            # 重置配额
            self.rate_limit_remaining = 100  # 默认值，子类可以覆盖
        return True

    def consume_rate_limit(self):
        """消耗一次配额"""
        if self.rate_limit_remaining > 0:
            self.rate_limit_remaining -= 1

    def _update_status(self):
        """更新数据源状态"""
        if self.consecutive_failures >= 3:
            self.status = DataSourceStatus.FAILED
        elif self.consecutive_failures >= 1 or self.failure_count > self.success_count:
            self.status = DataSourceStatus.DEGRADED
        else:
            self.status = DataSourceStatus.HEALTHY

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
        self.priority = priority  # 优先级，数字越小优先级越高
        self.metrics = SourceMetrics(name=name, source_type=source_type)
        self.capability = self._get_capability()
        self._lock = threading.Lock()

    @abstractmethod
    def _get_capability(self) -> SourceCapability:
        """定义数据源能力"""
        pass

    @abstractmethod
    def _check_config(self) -> bool:
        """检查配置是否完整（如token等）"""
        pass

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
        """
        if not self.is_available() or not self.supports(data_type):
            return -1.0

        success_rate = self.metrics.get_success_rate()
        avg_time = self.metrics.get_avg_time()

        # 速度评分（假设1秒为满分，超过5秒为0分）
        speed_score = max(0, 1 - (avg_time - 1) / 4)

        # 优先级评分（优先级数字越小分数越高）
        priority_score = max(0, 1 - self.priority / 100)

        # 类型匹配加分
        type_bonus = 0
        if self.source_type == SourceType.FREE_HIGH_FREQ:
            type_bonus = 0.2  # 免费高频优先使用

        # 综合评分
        return success_rate * 0.5 + speed_score * 0.3 + priority_score * 0.2 + type_bonus

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
    fallback_on_error: bool = True          # 出错时是否降级到其他数据源
    max_retries: int = 3                    # 最大重试次数


@dataclass
class QueryResult:
    """查询结果"""
    data: Any
    source: str
    source_type: SourceType
    cached: bool = False
    elapsed: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
