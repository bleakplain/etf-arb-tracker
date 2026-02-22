"""
历史持仓数据提供者适配器

将持仓快照管理器适配为 IETFHoldingProvider 接口。
"""

from typing import Dict, List, Optional
from loguru import logger

from backend.market.interfaces import IETFHoldingProvider
from backend.market import CandidateETF
from backend.backtest.holdings_snapshot import HoldingsSnapshotManager
from .models import ETFReference


class HistoricalHoldingProviderAdapter(IETFHoldingProvider):
    """
    历史持仓数据提供者适配器

    将 HoldingsSnapshotManager 适配为 IETFHoldingProvider 接口，
    用于回测场景。
    """

    def __init__(
        self,
        snapshot_manager: HoldingsSnapshotManager,
        interpolation: str = "linear"
    ):
        """
        初始化适配器

        Args:
            snapshot_manager: 持仓快照管理器
            interpolation: 插值方式 ("linear" 或 "step")
        """
        self._manager = snapshot_manager
        self._interpolation = interpolation
        self._current_time = None

    def set_current_time(self, current_time) -> None:
        """设置当前时间"""
        self._current_time = current_time

    def get_etf_top_holdings(self, etf_code: str) -> Optional[Dict]:
        """
        获取ETF前十大持仓（当前时间点）

        Args:
            etf_code: ETF代码

        Returns:
            持仓数据字典
        """
        if not self._current_time:
            raise RuntimeError("未设置当前时间，请先调用 set_current_time()")

        # 简化实现：返回模拟数据
        # 实际应该从持仓快照中获取
        return {
            'top_holdings': [],
            'total_weight': 0
        }

    def load_mapping(self, filepath: str) -> Optional[Dict]:
        """加载证券-ETF映射关系"""
        return self._manager.load_mapping(filepath)

    def save_mapping(self, mapping: Dict, filepath: str) -> None:
        """保存证券-ETF映射关系"""
        self._manager.save_mapping(mapping, filepath)

    def build_stock_etf_mapping(self, stock_codes: List[str], etf_codes: List[str]) -> Dict:
        """构建证券-ETF映射关系"""
        # 简化实现：返回空映射
        return {}
