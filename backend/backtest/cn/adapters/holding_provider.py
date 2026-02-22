"""
历史持仓数据提供者适配器

将持仓快照管理器适配为 IETFHoldingProvider 接口。
"""

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from backend.market.interfaces import IETFHoldingProvider
from backend.market import CandidateETF, ETFHolding
from backend.backtest.holdings_snapshot import HoldingsSnapshotManager


class HistoricalHoldingProviderAdapter(IETFHoldingProvider):
    """
    历史持仓数据提供者适配器

    将 HoldingsSnapshotManager 适配为 IETFHoldingProvider 接口，
    用于回测场景。该适配器利用持仓快照管理器获取指定时间点的
    股票-ETF关系，并支持插值。
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
        self._current_time: Optional[datetime] = None

        # 缓存当前时间点的ETF持仓数据，避免重复查询
        self._etf_holdings_cache: Dict[str, List[ETFHolding]] = {}

        # 缓存当前时间点的股票-ETF反向映射
        self._stock_etf_map: Dict[str, List[CandidateETF]] = {}

    def set_current_time(self, current_time: datetime) -> None:
        """
        设置当前时间

        Args:
            current_time: 当前模拟时间
        """
        if self._current_time != current_time:
            self._current_time = current_time
            # 清空缓存，因为时间已改变
            self._etf_holdings_cache.clear()
            self._stock_etf_map.clear()
            logger.debug(f"更新持仓时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

    def get_etf_top_holdings(self, etf_code: str) -> Optional[Dict]:
        """
        获取ETF前十大持仓（当前时间点）

        注意：这个方法是为了满足 IETFHoldingProvider 接口。
        在回测场景中，我们通常需要的是"哪些ETF持有某只股票"，
        而不是"某只ETF持有哪些股票"。因此，这个方法返回空列表。

        如果需要完整的ETF持仓数据，需要扩展快照数据结构。

        Args:
            etf_code: ETF代码

        Returns:
            空的持仓数据字典
        """
        return {
            'top_holdings': [],
            'total_weight': 0
        }

    def get_etfs_holding_stock(self, stock_code: str) -> List[CandidateETF]:
        """
        获取持有指定股票的ETF列表（当前时间点）

        这是回测场景的核心方法，用于查找哪些ETF持有涨停股票。

        Args:
            stock_code: 股票代码

        Returns:
            ETF引用列表，按权重降序排列
        """
        if not self._current_time:
            raise RuntimeError(
                "未设置当前时间，请先调用 set_current_time()"
            )

        # 检查缓存
        if stock_code in self._stock_etf_map:
            return self._stock_etf_map[stock_code]

        # 从快照管理器获取持仓数据
        holdings = self._manager.get_holdings_at_date(
            stock_code=stock_code,
            target_date=self._current_time,
            interpolation=self._interpolation
        )

        # 缓存结果
        self._stock_etf_map[stock_code] = holdings
        return holdings

    def load_mapping(self, filepath: str) -> Optional[Dict]:
        """
        加载证券-ETF映射关系

        委托给快照管理器处理。

        Args:
            filepath: 映射文件路径

        Returns:
            映射数据字典
        """
        return self._manager.load_mapping(filepath)

    def save_mapping(self, mapping: Dict, filepath: str) -> None:
        """
        保存证券-ETF映射关系

        委托给快照管理器处理。

        Args:
            mapping: 映射数据字典
            filepath: 映射文件路径
        """
        self._manager.save_mapping(mapping, filepath)

    def build_stock_etf_mapping(
        self,
        stock_codes: List[str],
        etf_codes: List[str]
    ) -> Dict:
        """
        构建证券-ETF映射关系

        这个方法在回测场景中不适用，因为我们使用快照管理器
        来获取历史持仓数据。返回空字典。

        Args:
            stock_codes: 股票代码列表
            etf_codes: ETF代码列表

        Returns:
            空字典
        """
        logger.warning(
            "回测场景不应调用 build_stock_etf_mapping，"
            "应使用 HoldingsSnapshotManager 获取历史数据"
        )
        return {}

    def get_snapshot_summary(self) -> Dict:
        """
        获取快照摘要信息

        Returns:
            快照摘要字典
        """
        return self._manager.get_snapshot_summary()

    def clear_cache(self) -> None:
        """清空缓存"""
        self._etf_holdings_cache.clear()
        self._stock_etf_map.clear()
        logger.debug("持仓适配器缓存已清空")
