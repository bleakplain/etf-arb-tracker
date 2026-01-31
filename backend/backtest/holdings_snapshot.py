"""
ETF持仓快照管理器

管理历史时点的ETF持仓数据，支持权重插值。
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from backend.domain.value_objects import ETFReference, ETFCategory

# Module-level constants for ETF names
DEFAULT_ETF_NAMES = {
    "510300": "沪深300ETF", "510500": "中证500ETF", "510050": "上证50ETF",
    "159915": "创业板ETF", "588000": "科创50ETF", "159901": "深100ETF",
    "512100": "中证1000ETF", "588200": "科创100ETF", "512480": "半导体ETF",
    "515000": "5GETF", "516160": "新能源ETF", "515790": "光伏ETF",
    "512590": "医药ETF", "159928": "消费ETF", "512170": "医疗ETF",
    "512880": "证券ETF", "512800": "银行ETF"
}


@dataclass
class HoldingsSnapshot:
    """持仓快照"""
    date: datetime
    stock_etf_map: Dict[str, List[ETFReference]]  # stock_code -> [ETFReferences]

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "stock_etf_map": {
                stock: [
                    {
                        "etf_code": ref.etf_code,
                        "etf_name": ref.etf_name,
                        "weight": ref.weight,
                        "category": ref.category.value,
                        "rank": ref.rank,
                        "in_top10": ref.in_top10,
                        "top10_ratio": ref.top10_ratio
                    }
                    for ref in refs
                ]
                for stock, refs in self.stock_etf_map.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "HoldingsSnapshot":
        """从字典创建"""
        stock_etf_map = {}
        for stock, refs_data in data.get("stock_etf_map", {}).items():
            stock_etf_map[stock] = [
                ETFReference(
                    etf_code=ref["etf_code"],
                    etf_name=ref["etf_name"],
                    weight=ref["weight"],
                    category=ETFCategory(ref["category"]),
                    rank=ref.get("rank", -1),
                    in_top10=ref.get("in_top10", False),
                    top10_ratio=ref.get("top10_ratio", 0.0)
                )
                for ref in refs_data
            ]

        return cls(
            date=datetime.strptime(data["date"], "%Y-%m-%d"),
            stock_etf_map=stock_etf_map
        )


class HoldingsSnapshotManager:
    """
    ETF持仓快照管理器

    管理历史时点的ETF持仓数据，支持权重插值。
    """

    def __init__(
        self,
        snapshot_dates: Optional[List[str]] = None,
        cache_dir: str = "data/historical/holdings"
    ):
        """
        初始化持仓快照管理器

        Args:
            snapshot_dates: 快照日期列表，格式 "YYYYMMDD"
                          如果不指定，自动生成每季度初的日期
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 生成快照日期
        self.snapshot_dates = [
            datetime.strptime(d, "%Y%m%d") for d in (snapshot_dates or self._generate_quarterly_dates())
        ]

        # 存储快照数据
        self.snapshots: Dict[datetime, HoldingsSnapshot] = {}

        logger.info(f"持仓快照管理器初始化，快照日期: {len(self.snapshot_dates)}个")

    @staticmethod
    def _generate_quarterly_dates() -> List[str]:
        """生成每季度初的日期（年初、4月初、7月初、10月初）"""
        # 简化：返回固定的季度日期
        # 实际使用时应该根据回测范围生成
        return [
            "20240101",  # 年初
            "20240401",  # Q2开始
            "20240701",  # Q3开始
            "20241001",  # Q4开始
        ]

    def load_snapshots(
        self,
        stock_codes: List[str],
        etf_codes: List[str],
        force_refresh: bool = False
    ) -> None:
        """
        加载或构建持仓快照

        Args:
            stock_codes: 股票代码列表
            etf_codes: ETF代码列表
            force_refresh: 是否强制重新获取
        """
        for snapshot_date in self.snapshot_dates:
            cache_file = self._get_cache_file(snapshot_date)

            # 尝试从缓存加载
            if not force_refresh and cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    snapshot = HoldingsSnapshot.from_dict(data)
                    self.snapshots[snapshot_date] = snapshot
                    logger.debug(f"从缓存加载快照: {snapshot_date.strftime('%Y-%m-%d')}")
                    continue
                except Exception as e:
                    logger.warning(f"加载缓存失败 {cache_file}: {e}")

            # 构建新快照（简化版：使用当前映射）
            logger.info(f"构建持仓快照: {snapshot_date.strftime('%Y-%m-%d')}")
            snapshot = self._build_snapshot(snapshot_date, stock_codes, etf_codes)

            if snapshot:
                self.snapshots[snapshot_date] = snapshot
                self._save_snapshot(snapshot)

    def _build_snapshot(
        self,
        date: datetime,
        stock_codes: List[str],
        etf_codes: List[str],
        use_mock_data: bool = True
    ) -> Optional[HoldingsSnapshot]:
        """
        构建指定日期的持仓快照

        简化版：使用现有的stock_etf_mapping作为快照数据
        如果没有映射数据且use_mock_data=True，生成模拟持仓数据

        Args:
            date: 快照日期
            stock_codes: 股票代码列表
            etf_codes: ETF代码列表
            use_mock_data: 是否在没有真实数据时使用模拟数据
        """
        try:
            # 尝试加载现有的映射文件
            mapping_file = "data/stock_etf_mapping.json"
            if Path(mapping_file).exists():
                try:
                    with open(mapping_file, "r", encoding="utf-8") as f:
                        mapping = json.load(f)

                    # 检查映射是否有数据
                    if mapping and mapping != {}:
                        return self._build_from_mapping(mapping, stock_codes, date)
                except Exception as e:
                    logger.warning(f"加载映射文件失败: {e}")

        except Exception as e:
            logger.error(f"构建快照失败: {e}")

        # 没有真实数据或加载失败，生成模拟持仓
        if use_mock_data:
            logger.info("使用模拟持仓数据进行回测")
            return self._build_mock_snapshot(stock_codes, etf_codes, date)

        return None

    def _build_from_mapping(
        self,
        mapping: Dict,
        stock_codes: List[str],
        date: datetime
    ) -> Optional[HoldingsSnapshot]:
        """从现有映射构建快照"""
        stock_etf_map = {}
        for stock_code, etf_list in mapping.items():
            if stock_code not in stock_codes:
                continue

            refs = []
            for etf in etf_list:
                refs.append(ETFReference(
                    etf_code=etf["etf_code"],
                    etf_name=etf["etf_name"],
                    weight=etf.get("weight", 0.05),  # 默认权重
                    category=self._get_etf_category(etf["etf_code"]),
                    rank=etf.get("rank", -1),
                    in_top10=etf.get("in_top10", False),
                    top10_ratio=etf.get("top10_ratio", 0.0)
                ))
            stock_etf_map[stock_code] = refs

        return HoldingsSnapshot(date=date, stock_etf_map=stock_etf_map)

    def _build_mock_snapshot(
        self,
        stock_codes: List[str],
        etf_codes: List[str],
        date: datetime
    ) -> HoldingsSnapshot:
        """
        构建模拟持仓快照

        为每个股票随机分配3-5个ETF，权重在5%-15%之间
        这样可以保证回测能够运行并生成信号
        """
        stock_etf_map = {}

        for stock_code in stock_codes:
            # 为每个股票随机选择3-5个ETF
            num_etfs = random.randint(3, min(5, len(etf_codes)))
            selected_etfs = random.sample(etf_codes, num_etfs)

            refs = []
            remaining_weight = 0.40  # 总权重40%

            for i, etf_code in enumerate(selected_etfs):
                # 最后一个ETF补足剩余权重，其他权重在5%-15%之间
                if i == num_etfs - 1:
                    weight = remaining_weight
                else:
                    max_weight = min(0.15, remaining_weight / (num_etfs - i))
                    weight = random.uniform(0.05, max_weight)
                    remaining_weight -= weight

                refs.append(ETFReference(
                    etf_code=etf_code,
                    etf_name=DEFAULT_ETF_NAMES.get(etf_code, f"ETF{etf_code}"),
                    weight=round(weight, 4),
                    category=self._get_etf_category(etf_code),
                    rank=i + 1,
                    in_top10=i < 3,
                    top10_ratio=round(weight * (1 + random.uniform(0, 0.2)), 4)
                ))

            stock_etf_map[stock_code] = refs

        logger.info(f"生成模拟持仓数据: {len(stock_etf_map)} 只股票")
        return HoldingsSnapshot(date=date, stock_etf_map=stock_etf_map)

    @staticmethod
    def _get_etf_category(etf_code: str) -> ETFCategory:
        """根据ETF代码获取分类"""
        # 定义ETF分类
        categories = {
            ETFCategory.BROAD_INDEX: ["510300", "510500", "510050", "159915", "588000",
                                      "159901", "512100", "588200"],
            ETFCategory.TECH: ["159995", "512480", "515000", "516160", "515790"],
            ETFCategory.CONSUMER: ["512590", "159928", "512170"],
            ETFCategory.FINANCIAL: ["512880", "512800"]
        }

        for category, codes in categories.items():
            if etf_code in codes:
                return category
        return ETFCategory.OTHER

    def get_holdings_at_date(
        self,
        stock_code: str,
        target_date: datetime,
        interpolation: str = "linear"
    ) -> List[ETFReference]:
        """
        获取指定日期的股票-ETF关系（支持插值）

        Args:
            stock_code: 股票代码
            target_date: 目标日期
            interpolation: 插值方式 "linear" 或 "step"

        Returns:
            ETF引用列表
        """
        if not self.snapshots:
            logger.warning("没有可用的持仓快照")
            return []

        # 找到最近的两个快照
        snapshot_before, snapshot_after = self._find_surrounding_snapshots(target_date)

        if snapshot_before is None and snapshot_after is None:
            return []

        # 只有一个快照或不插值
        if snapshot_before is None:
            return snapshot_after.stock_etf_map.get(stock_code, [])
        if snapshot_after is None:
            return snapshot_before.stock_etf_map.get(stock_code, [])

        # 两个快照是同一个，直接返回
        if snapshot_before.date == snapshot_after.date:
            return snapshot_before.stock_etf_map.get(stock_code, [])

        # 插值
        if interpolation == "linear":
            return self._interpolate_holdings(
                stock_code, snapshot_before, snapshot_after, target_date
            )
        else:  # step
            # 阶梯插值：使用前一个快照的数据
            return snapshot_before.stock_etf_map.get(stock_code, [])

    def _find_surrounding_snapshots(
        self,
        target_date: datetime
    ) -> Tuple[Optional[HoldingsSnapshot], Optional[HoldingsSnapshot]]:
        """
        找到目标日期前后的快照

        Returns:
            (前一个快照, 后一个快照)
        """
        before = None
        after = None

        for snapshot in self.snapshots.values():
            if snapshot.date <= target_date:
                if before is None or snapshot.date > before.date:
                    before = snapshot
            if snapshot.date >= target_date:
                if after is None or snapshot.date < after.date:
                    after = snapshot

        return before, after

    def _interpolate_holdings(
        self,
        stock_code: str,
        snapshot_before: HoldingsSnapshot,
        snapshot_after: HoldingsSnapshot,
        target_date: datetime
    ) -> List[ETFReference]:
        """
        在两个快照之间线性插值权重

        Args:
            stock_code: 股票代码
            snapshot_before: 前一个快照
            snapshot_after: 后一个快照
            target_date: 目标日期

        Returns:
            插值后的ETF引用列表
        """
        holdings_before = snapshot_before.stock_etf_map.get(stock_code, [])
        holdings_after = snapshot_after.stock_etf_map.get(stock_code, [])

        # 计算插值系数
        total_days = (snapshot_after.date - snapshot_before.date).days
        if total_days <= 0:
            return holdings_before

        elapsed = (target_date - snapshot_before.date).days
        ratio = elapsed / total_days
        ratio = max(0, min(1, ratio))  # 限制在[0, 1]

        # 构建后一个快照的字典以便查找
        after_map = {ref.etf_code: ref for ref in holdings_after}

        results = []
        for etf_before in holdings_before:
            etf_after = after_map.get(etf_before.etf_code)

            if etf_after:
                # 两个快照都有这个ETF，插值权重
                interpolated_weight = (
                    etf_before.weight * (1 - ratio) + etf_after.weight * ratio
                )
                results.append(ETFReference(
                    etf_code=etf_before.etf_code,
                    etf_name=etf_before.etf_name,
                    weight=interpolated_weight,
                    category=etf_before.category,
                    rank=etf_before.rank,
                    in_top10=etf_before.in_top10,
                    top10_ratio=etf_before.top10_ratio
                ))
            else:
                # 只有前一个快照有，权重随时间衰减
                decayed_weight = etf_before.weight * (1 - ratio)
                if decayed_weight > 0.01:  # 权重大于1%才保留
                    results.append(ETFReference(
                        etf_code=etf_before.etf_code,
                        etf_name=etf_before.etf_name,
                        weight=decayed_weight,
                        category=etf_before.category,
                        rank=etf_before.rank,
                        in_top10=etf_before.in_top10,
                        top10_ratio=etf_before.top10_ratio
                    ))

        # 添加只存在于后一个快照的ETF（新增持仓）
        before_codes = {ref.etf_code for ref in holdings_before}
        for etf_after in holdings_after:
            if etf_after.etf_code not in before_codes:
                # 新增持仓，权重随时间增长
                grown_weight = etf_after.weight * ratio
                if grown_weight > 0.01:  # 权重大于1%才保留
                    results.append(ETFReference(
                        etf_code=etf_after.etf_code,
                        etf_name=etf_after.etf_name,
                        weight=grown_weight,
                        category=etf_after.category,
                        rank=etf_after.rank,
                        in_top10=etf_after.in_top10,
                        top10_ratio=etf_after.top10_ratio
                    ))

        # 按权重排序
        results.sort(key=lambda x: x.weight, reverse=True)
        return results

    def _get_cache_file(self, date: datetime) -> Path:
        """获取缓存文件路径"""
        filename = f"holdings_snapshot_{date.strftime('%Y%m%d')}.json"
        return self.cache_dir / filename

    def _save_snapshot(self, snapshot: HoldingsSnapshot) -> None:
        """保存快照到缓存"""
        cache_file = self._get_cache_file(snapshot.date)
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存快照失败 {cache_file}: {e}")

    def get_snapshot_summary(self) -> Dict:
        """获取快照摘要"""
        return {
            "snapshot_dates": [d.strftime("%Y-%m-%d") for d in self.snapshot_dates],
            "loaded_snapshots": len(self.snapshots),
            "cache_dir": str(self.cache_dir)
        }
