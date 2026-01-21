"""
数据管理器 - 新多数据源架构
支持免费高频和付费低频相结合的策略
"""

import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger
from datetime import datetime
import pandas as pd

from backend.data.source_base import (
    BaseDataSource,
    SourceType,
    DataType,
    DataSourceStatus,
    QueryContext,
    QueryResult
)
from backend.data.sources import TencentDataSource, SinaDataSource, TushareDataSource


class DataManager:
    """
    数据管理器 - 统一管理所有数据源

    策略：
    1. 实时行情优先使用免费高频数据源（腾讯、新浪）
    2. 财务/历史数据使用付费数据源（Tushare）
    3. 自动故障转移
    4. 智能数据源选择
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config: Optional[Dict] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[Dict] = None):
        if self._initialized:
            return

        self.config = config or {}
        self.sources: List[BaseDataSource] = []
        self._stock_codes_cache: Optional[List[str]] = None
        self._lock = threading.Lock()

        self._initialize_sources()
        self._initialized = True

        logger.info("数据管理器初始化完成")

    def _initialize_sources(self):
        """初始化所有数据源"""
        # 读取配置
        sources_config = self.config.get('data_sources', {})

        # 免费高频数据源
        tencent_enabled = sources_config.get('tencent', {}).get('enabled', True)
        sina_enabled = sources_config.get('sina', {}).get('enabled', True)

        # 付费数据源
        tushare_config = sources_config.get('tushare', {})
        tushare_enabled = tushare_config.get('enabled', False)
        tushare_token = tushare_config.get('token', '') or self.config.get('tushare_token', '')

        # 按优先级添加数据源
        if tencent_enabled:
            priority = sources_config.get('tencent', {}).get('priority', 1)
            self.sources.append(TencentDataSource(priority=priority))
            logger.info("已添加腾讯数据源")

        if sina_enabled:
            priority = sources_config.get('sina', {}).get('priority', 2)
            self.sources.append(SinaDataSource(priority=priority))
            logger.info("已添加新浪数据源")

        if tushare_enabled and tushare_token:
            priority = sources_config.get('tushare', {}).get('priority', 10)
            self.sources.append(TushareDataSource(token=tushare_token, priority=priority))
            logger.info("已添加Tushare数据源")

        # 按优先级排序
        self.sources.sort(key=lambda x: x.priority)

        logger.info(f"数据源初始化完成，共 {len(self.sources)} 个数据源")
        for source in self.sources:
            logger.info(f"  - {source.name} (type={source.source_type.value}, priority={source.priority})")

    def _get_available_sources(self, data_type: DataType) -> List[BaseDataSource]:
        """获取支持指定数据类型的可用数据源"""
        available = []
        for source in self.sources:
            if source.is_available() and source.supports(data_type):
                available.append(source)

        # 按评分排序
        available.sort(key=lambda s: s.get_score(data_type), reverse=True)
        return available

    def _try_source(
        self,
        source: BaseDataSource,
        method_name: str,
        *args,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """尝试从指定数据源获取数据"""
        if not source.metrics.should_retry_now():
            logger.debug(f"数据源 {source.name} 在冷却期，跳过")
            return None

        try:
            source.metrics.last_attempt_time = datetime.now()
            method = getattr(source, method_name)
            return method(*args, **kwargs)
        except Exception as e:
            source.metrics.record_failure()
            logger.debug(f"数据源 {source.name} 请求失败: {e}")
            return None

    def fetch_stock_spot(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取股票实时行情

        策略：优先使用免费高频数据源

        Args:
            codes: 股票代码列表，None表示获取所有

        Returns:
            股票行情DataFrame
        """
        available = self._get_available_sources(DataType.STOCK_REALTIME)

        if not available:
            logger.error("没有可用的股票行情数据源")
            return pd.DataFrame()

        last_error = None

        for source in available:
            logger.debug(f"尝试使用 {source.name} 获取股票行情...")

            # 对于需要指定代码的数据源，需要提供codes
            if codes is None and source.name in ['tencent', 'sina']:
                # 尝试使用缓存的代码列表
                codes = self._stock_codes_cache or self._get_common_stock_codes()
                if not codes:
                    logger.warning(f"{source.name} 需要指定股票代码，跳过")
                    continue

            result = self._try_source(source, 'fetch_stock_spot', codes)

            if result is not None and not result.empty:
                # 缓存股票代码列表
                if '代码' in result.columns:
                    self._stock_codes_cache = result['代码'].tolist()[:2000]
                return result

            last_error = f"{source.name} 失败"

        logger.warning(f"所有数据源均失败: {last_error}")
        return pd.DataFrame()

    def fetch_etf_spot(self, codes: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取ETF实时行情

        Args:
            codes: ETF代码列表，None表示获取常用ETF

        Returns:
            ETF行情DataFrame
        """
        available = self._get_available_sources(DataType.ETF_REALTIME)

        if not available:
            logger.error("没有可用的ETF行情数据源")
            return pd.DataFrame()

        last_error = None

        for source in available:
            logger.debug(f"尝试使用 {source.name} 获取ETF行情...")

            # 对于需要指定代码的数据源，需要提供codes
            if codes is None and source.name in ['tencent', 'sina']:
                # 使用常用ETF代码列表
                codes = self._get_common_etf_codes()
                if not codes:
                    logger.warning(f"{source.name} 需要指定ETF代码，跳过")
                    continue

            result = self._try_source(source, 'fetch_etf_spot', codes)

            if result is not None and not result.empty:
                return result

            last_error = f"{source.name} 失败"

        logger.warning(f"所有数据源均失败: {last_error}")
        return pd.DataFrame()

    def fetch_stock_history(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取股票历史行情

        策略：优先使用付费数据源

        Args:
            stock_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            历史行情DataFrame
        """
        available = self._get_available_sources(DataType.STOCK_HISTORY)

        if not available:
            logger.error("没有可用的历史数据源")
            return pd.DataFrame()

        for source in available:
            logger.debug(f"尝试使用 {source.name} 获取历史行情...")

            result = self._try_source(
                source,
                'fetch_stock_history',
                stock_code,
                start_date,
                end_date
            )

            if result is not None and not result.empty:
                return result

        return pd.DataFrame()

    def fetch_financial(
        self,
        stock_code: str,
        report_type: str = "income"
    ) -> pd.DataFrame:
        """
        获取财务数据

        策略：使用付费数据源

        Args:
            stock_code: 股票代码
            report_type: 报表类型 income/balance/cashflow

        Returns:
            财务数据DataFrame
        """
        available = self._get_available_sources(DataType.FINANCIAL)

        if not available:
            logger.error("没有可用的财务数据源")
            return pd.DataFrame()

        for source in available:
            logger.debug(f"尝试使用 {source.name} 获取财务数据...")

            result = self._try_source(
                source,
                'fetch_financial',
                stock_code,
                report_type
            )

            if result is not None and not result.empty:
                return result

        return pd.DataFrame()

    def get_stock_list(self) -> pd.DataFrame:
        """获取所有股票列表"""
        available = self._get_available_sources(DataType.STOCK_REALTIME)

        for source in available:
            if hasattr(source, 'fetch_stock_list'):
                result = self._try_source(source, 'fetch_stock_list')
                if result is not None and not result.empty:
                    return result

        return pd.DataFrame()

    def _get_common_stock_codes(self) -> List[str]:
        """获取常用股票代码列表"""
        # 这里可以配置常用股票列表
        # 或者从文件读取
        common_codes = [
            # 上证权重
            "600519", "600036", "601318", "601012", "600276",
            # 深证权重
            "000001", "000002", "000333", "000651", "002594",
            # 创业板
            "300750", "300059", "300015", "300142", "300274",
            # 科创板
            "688981", "688111", "688599", "688036", "688012",
        ]
        return common_codes

    def _get_common_etf_codes(self) -> List[str]:
        """获取常用ETF代码列表"""
        # 主要ETF列表
        common_etf_codes = [
            # 宽基ETF
            "510300", "510500", "159915", "588000", "512880",
            "512100", "512000", "159919", "510210", "510310",
            # 行业ETF
            "512690", "512480", "512400", "512170", "512660",
            "512800", "515000", "512880", "515030", "512980",
        ]
        return common_etf_codes

    def set_common_stocks(self, codes: List[str]):
        """设置常用股票代码列表"""
        self._stock_codes_cache = codes
        # 更新腾讯数据源的常用股票
        for source in self.sources:
            if hasattr(source, 'set_common_stocks'):
                source.set_common_stocks(codes)
        logger.info(f"已设置常用股票列表: {len(codes)} 只")

    def get_metrics(self) -> Dict:
        """获取所有数据源的指标"""
        metrics = {}
        for source in self.sources:
            metrics[source.name] = {
                'type': source.source_type.value,
                'priority': source.priority,
                'status': source.metrics.status.value,
                'request_count': source.metrics.request_count,
                'success_count': source.metrics.success_count,
                'failure_count': source.metrics.failure_count,
                'success_rate': source.metrics.get_success_rate(),
                'avg_time': source.metrics.get_avg_time(),
                'configured': source.is_configured(),
                'available': source.is_available(),
            }
        return metrics

    def reset_metrics(self):
        """重置所有数据源的指标"""
        for source in self.sources:
            source.reset_metrics()
        logger.info("已重置所有数据源的指标")

    def get_best_source(self, data_type: DataType) -> Optional[BaseDataSource]:
        """获取最佳数据源"""
        available = self._get_available_sources(data_type)
        if not available:
            return None
        return available[0]  # 已排序

    def reload_config(self, config: Dict):
        """重新加载配置"""
        self.config = config
        self.sources.clear()
        self._stock_codes_cache = None
        self._initialize_sources()
        logger.info("配置已重新加载")


# 全局单例
_data_manager: Optional[DataManager] = None


def get_data_manager(config: Optional[Dict] = None) -> DataManager:
    """获取数据管理器单例"""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager(config)
    elif config is not None:
        _data_manager.reload_config(config)
    return _data_manager


# 测试代码
if __name__ == "__main__":
    # 测试配置
    test_config = {
        'data_sources': {
            'tencent': {'enabled': True, 'priority': 1},
            'sina': {'enabled': True, 'priority': 2},
            'tushare': {'enabled': False, 'priority': 10},
        }
    }

    manager = get_data_manager(test_config)

    print("=" * 60)
    print("测试数据管理器")
    print("=" * 60)

    # 测试获取股票行情
    print("\n=== 测试获取股票行情 ===")
    codes = ["600519", "000001", "300750", "510300"]
    df = manager.fetch_stock_spot(codes)

    if not df.empty:
        print(f"成功获取 {len(df)} 只股票:")
        print(df[['代码', '名称', '最新价', '涨跌幅']].to_string())
    else:
        print("获取失败")

    # 显示指标
    print("\n=== 数据源指标 ===")
    metrics = manager.get_metrics()
    for name, metric in metrics.items():
        print(f"{name}: {metric}")
