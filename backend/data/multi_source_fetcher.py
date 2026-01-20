"""
多数据源管理器
支持多个数据源，自动降级和故障转移
"""

import time
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from enum import Enum
from loguru import logger
import pandas as pd
from datetime import datetime
import threading


class DataSourceStatus(Enum):
    """数据源状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class DataSourceMetric:
    """数据源性能指标"""

    def __init__(self, name: str):
        self.name = name
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_time = 0.0
        self.last_success_time = None
        self.last_failure_time = None
        self.consecutive_failures = 0
        self.status = DataSourceStatus.HEALTHY

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
        self.consecutive_failures += 1
        self._update_status()

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
        return self.status != DataSourceStatus.FAILED

    def __repr__(self):
        return (f"DataSourceMetric({self.name}, "
                f"status={self.status.value}, "
                f"success_rate={self.get_success_rate():.1%}, "
                f"avg_time={self.get_avg_time():.2f}s, "
                f"consecutive_failures={self.consecutive_failures})")


class BaseDataSource(ABC):
    """数据源基类"""

    def __init__(self, name: str, priority: int = 0):
        self.name = name
        self.priority = priority  # 优先级，数字越小优先级越高
        self.metric = DataSourceMetric(name)

    @abstractmethod
    def fetch_stock_spot(self) -> pd.DataFrame:
        """获取A股实时行情"""
        pass

    @abstractmethod
    def fetch_etf_spot(self) -> pd.DataFrame:
        """获取ETF实时行情"""
        pass

    def is_available(self) -> bool:
        """判断数据源是否可用"""
        return self.metric.is_available()


class EFinanceDataSource(BaseDataSource):
    """EFinance数据源 - 主数据源"""

    def __init__(self):
        super().__init__("efinance", priority=1)
        self._import_efinance()

    def _import_efinance(self):
        """延迟导入efinance"""
        try:
            import efinance
            self.ef = efinance
            logger.info("EFinance数据源初始化成功")
        except ImportError:
            logger.error("EFinance未安装，请运行: pip install efinance")
            self.ef = None

    def fetch_stock_spot(self) -> pd.DataFrame:
        """获取A股实时行情"""
        if self.ef is None:
            raise ImportError("EFinance未安装")

        start_time = time.time()
        try:
            logger.debug(f"使用 {self.name} 获取A股实时行情...")
            # 使用efinance获取股票实时行情
            df = self.ef.stock.get_realtime_quotes()

            if df is None or df.empty:
                raise ValueError("返回数据为空")

            # 标准化列名以匹配AKShare格式
            df = self._standardize_columns(df, is_stock=True)

            elapsed = time.time() - start_time
            self.metric.record_success(elapsed)
            logger.info(f"{self.name} 成功获取 {len(df)} 只A股 (耗时: {elapsed:.2f}秒)")
            return df

        except Exception as e:
            elapsed = time.time() - start_time
            self.metric.record_failure()
            logger.error(f"{self.name} 获取A股行情失败: {e}")
            raise

    def fetch_etf_spot(self) -> pd.DataFrame:
        """获取ETF实时行情"""
        if self.ef is None:
            raise ImportError("EFinance未安装")

        start_time = time.time()
        try:
            logger.debug(f"使用 {self.name} 获取ETF实时行情...")
            # efinance暂不支持批量获取ETF，直接fallback到AKShare
            # 抛出异常让系统切换到备用数据源
            raise NotImplementedError("efinance暂不支持批量获取ETF数据，将自动使用AKShare")

        except Exception as e:
            elapsed = time.time() - start_time
            self.metric.record_failure()
            logger.debug(f"{self.name} 获取ETF行情失败: {e}")
            raise

    def _standardize_columns(self, df: pd.DataFrame, is_stock: bool = True) -> pd.DataFrame:
        """标准化列名以匹配AKShare格式"""
        if df.empty:
            return df

        # efinance列名映射到AKShare格式
        column_mapping = {
            '股票代码': '代码',
            '股票名称': '名称',
            '最新价': '最新价',
            '涨跌幅': '涨跌幅',
            '涨跌额': '涨跌额',
            '最高': '最高',
            '最低': '最低',
            '今开': '今开',
            '昨收': '昨收',
            '成交量': '成交量',
            '成交额': '成交额',
            '成交金额': '成交额',
            '换手率': '换手率',
            '市盈率': '市盈率',
            '市净率': '市净率',
            '总市值': '总市值',
            '流通市值': '流通市值',
            '代码': '代码',
            '名称': '名称',
            '基金代码': '代码',
            '基金名称': '名称',
        }

        # 重命名列
        df = df.rename(columns=column_mapping)

        # 确保必要列存在
        required_columns = ['代码', '名称', '最新价', '涨跌幅']
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"{self.name} 返回数据缺少列: {col}")

        return df


class AkshareDataSource(BaseDataSource):
    """AKShare数据源 - 备用数据源"""

    def __init__(self):
        super().__init__("akshare", priority=2)
        self._import_akshare()

    def _import_akshare(self):
        """延迟导入akshare"""
        try:
            import akshare as ak
            self.ak = ak
            logger.info("AKShare数据源初始化成功")
        except ImportError:
            logger.error("AKShare未安装，请运行: pip install akshare")
            self.ak = None

    def fetch_stock_spot(self) -> pd.DataFrame:
        """获取A股实时行情"""
        if self.ak is None:
            raise ImportError("AKShare未安装")

        start_time = time.time()
        try:
            logger.debug(f"使用 {self.name} 获取A股实时行情...")
            df = self.ak.stock_zh_a_spot_em()

            if df is None or df.empty:
                raise ValueError("返回数据为空")

            elapsed = time.time() - start_time
            self.metric.record_success(elapsed)
            logger.info(f"{self.name} 成功获取 {len(df)} 只A股 (耗时: {elapsed:.2f}秒)")
            return df

        except Exception as e:
            elapsed = time.time() - start_time
            self.metric.record_failure()
            logger.error(f"{self.name} 获取A股行情失败: {e}")
            raise

    def fetch_etf_spot(self) -> pd.DataFrame:
        """获取ETF实时行情"""
        if self.ak is None:
            raise ImportError("AKShare未安装")

        start_time = time.time()
        try:
            logger.debug(f"使用 {self.name} 获取ETF实时行情...")
            df = self.ak.fund_etf_spot_em()

            if df is None or df.empty:
                raise ValueError("返回数据为空")

            elapsed = time.time() - start_time
            self.metric.record_success(elapsed)
            logger.info(f"{self.name} 成功获取 {len(df)} 只ETF (耗时: {elapsed:.2f}秒)")
            return df

        except Exception as e:
            elapsed = time.time() - start_time
            self.metric.record_failure()
            logger.error(f"{self.name} 获取ETF行情失败: {e}")
            raise


class MultiSourceFetcher:
    """多数据源管理器 - 自动故障转移"""

    def __init__(self):
        self.sources: List[BaseDataSource] = []
        self._lock = threading.Lock()
        self._initialize_sources()

    def _initialize_sources(self):
        """初始化所有数据源"""
        # 按优先级添加数据源
        self.sources = [
            EFinanceDataSource(),  # 主数据源
            AkshareDataSource(),   # 备用数据源
        ]

        # 按优先级排序
        self.sources.sort(key=lambda x: x.priority)

        logger.info(f"多数据源管理器已初始化，数据源数量: {len(self.sources)}")
        for source in self.sources:
            logger.info(f"  - {source.name} (优先级: {source.priority})")

    def _get_available_sources(self) -> List[BaseDataSource]:
        """获取可用的数据源列表"""
        return [s for s in self.sources if s.is_available()]

    def _try_fetch(self, source: BaseDataSource, fetch_func_name: str, *args, **kwargs) -> Optional[pd.DataFrame]:
        """尝试从指定数据源获取数据"""
        try:
            fetch_func = getattr(source, fetch_func_name)
            return fetch_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"数据源 {source.name} 请求失败: {e}")
            return None

    def fetch_stock_spot(self) -> pd.DataFrame:
        """
        获取A股实时行情
        按优先级尝试所有可用数据源，直到成功
        """
        available_sources = self._get_available_sources()

        if not available_sources:
            logger.error("没有可用的数据源！")
            return pd.DataFrame()

        last_error = None

        for source in available_sources:
            logger.debug(f"尝试使用数据源: {source.name}")
            result = self._try_fetch(source, 'fetch_stock_spot')

            if result is not None and not result.empty:
                return result

            last_error = f"{source.name} 失败"

        # 所有数据源都失败，尝试强制使用第一个数据源
        logger.warning("所有可用数据源均失败，尝试强制使用主数据源...")
        for source in self.sources:
            result = self._try_fetch(source, 'fetch_stock_spot')
            if result is not None and not result.empty:
                return result

        logger.error(f"所有数据源均失败: {last_error}")
        return pd.DataFrame()

    def fetch_etf_spot(self) -> pd.DataFrame:
        """
        获取ETF实时行情
        按优先级尝试所有可用数据源，直到成功
        """
        available_sources = self._get_available_sources()

        if not available_sources:
            logger.error("没有可用的数据源！")
            return pd.DataFrame()

        last_error = None

        for source in available_sources:
            logger.debug(f"尝试使用数据源: {source.name}")
            result = self._try_fetch(source, 'fetch_etf_spot')

            if result is not None and not result.empty:
                return result

            last_error = f"{source.name} 失败"

        # 所有数据源都失败，尝试强制使用第一个数据源
        logger.warning("所有可用数据源均失败，尝试强制使用主数据源...")
        for source in self.sources:
            result = self._try_fetch(source, 'fetch_etf_spot')
            if result is not None and not result.empty:
                return result

        logger.error(f"所有数据源均失败: {last_error}")
        return pd.DataFrame()

    def get_metrics(self) -> Dict[str, Dict]:
        """获取所有数据源的性能指标"""
        metrics = {}
        for source in self.sources:
            metrics[source.name] = {
                'priority': source.priority,
                'status': source.metric.status.value,
                'request_count': source.metric.request_count,
                'success_count': source.metric.success_count,
                'failure_count': source.metric.failure_count,
                'success_rate': source.metric.get_success_rate(),
                'avg_time': source.metric.get_avg_time(),
                'consecutive_failures': source.metric.consecutive_failures,
                'last_success_time': source.metric.last_success_time.isoformat() if source.metric.last_success_time else None,
                'last_failure_time': source.metric.last_failure_time.isoformat() if source.metric.last_failure_time else None,
            }
        return metrics

    def get_best_source(self) -> Optional[BaseDataSource]:
        """获取最佳数据源（基于成功率和响应时间）"""
        available = self._get_available_sources()
        if not available:
            return None

        # 综合评分：成功率权重0.7，速度权重0.3
        def score(source: BaseDataSource) -> float:
            success_rate = source.metric.get_success_rate()
            avg_time = source.metric.get_avg_time()

            # 速度评分（假设1秒为满分，超过5秒为0分）
            speed_score = max(0, 1 - (avg_time - 1) / 4)

            return success_rate * 0.7 + speed_score * 0.3

        return max(available, key=score)

    def reset_metrics(self):
        """重置所有数据源的指标"""
        for source in self.sources:
            source.metric = DataSourceMetric(source.name)
        logger.info("已重置所有数据源的性能指标")


# 全局单例
_global_fetcher: Optional[MultiSourceFetcher] = None
_fetcher_lock = threading.Lock()


def get_multi_source_fetcher() -> MultiSourceFetcher:
    """获取全局多数据源管理器单例"""
    global _global_fetcher

    if _global_fetcher is None:
        with _fetcher_lock:
            if _global_fetcher is None:
                _global_fetcher = MultiSourceFetcher()

    return _global_fetcher


# 测试代码
if __name__ == "__main__":
    import time

    fetcher = get_multi_source_fetcher()

    print("=" * 60)
    print("测试多数据源管理器")
    print("=" * 60)

    # 测试获取A股行情
    print("\n=== 测试获取A股行情 ===")
    start = time.time()
    stock_df = fetcher.fetch_stock_spot()
    elapsed = time.time() - start

    if not stock_df.empty:
        print(f"成功获取 {len(stock_df)} 只A股，耗时: {elapsed:.2f}秒")
        print("\n前5只股票:")
        print(stock_df[['代码', '名称', '最新价', '涨跌幅']].head())
    else:
        print("获取A股行情失败")

    # 显示性能指标
    print("\n=== 数据源性能指标 ===")
    metrics = fetcher.get_metrics()
    for name, metric in metrics.items():
        print(f"\n{name}:")
        print(f"  状态: {metric['status']}")
        print(f"  成功率: {metric['success_rate']:.1%}")
        print(f"  平均响应时间: {metric['avg_time']:.2f}秒")
        print(f"  连续失败次数: {metric['consecutive_failures']}")

    # 测试获取ETF行情
    print("\n=== 测试获取ETF行情 ===")
    start = time.time()
    etf_df = fetcher.fetch_etf_spot()
    elapsed = time.time() - start

    if not etf_df.empty:
        print(f"成功获取 {len(etf_df)} 只ETF，耗时: {elapsed:.2f}秒")
        print("\n前5只ETF:")
        print(etf_df[['代码', '名称', '最新价', '涨跌幅']].head())
    else:
        print("获取ETF行情失败")

    # 显示最佳数据源
    best = fetcher.get_best_source()
    if best:
        print(f"\n最佳数据源: {best.name}")
