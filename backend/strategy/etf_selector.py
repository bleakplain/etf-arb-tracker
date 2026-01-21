"""
ETF选择器 - 专职选择合适的ETF
"""

from typing import List, Dict, Optional
from loguru import logger

from backend.domain.interfaces import IETFHolderProvider, IETFHoldingsProvider
from backend.domain.value_objects import ETFReference, ETFCategory


class ETFSelector:
    """
    ETF选择器

    职责：
    1. 查找与股票相关的ETF
    2. 获取股票在ETF中的真实权重
    3. 根据策略筛选符合条件的ETF
    """

    def __init__(
        self,
        holder_provider: IETFHolderProvider,
        holdings_provider: IETFHoldingsProvider,
        min_weight: float = 0.05
    ):
        """
        初始化ETF选择器

        Args:
            holder_provider: ETF持仓关系提供者
            holdings_provider: ETF持仓详情提供者
            min_weight: 最小持仓权重阈值
        """
        self._holder_provider = holder_provider
        self._holdings_provider = holdings_provider
        self._min_weight = min_weight
        self._mapping: Dict = {}

    def load_mapping(self, filepath: str = "data/stock_etf_mapping.json") -> None:
        """加载股票-ETF映射关系"""
        self._mapping = self._holder_provider.load_mapping(filepath) or {}
        logger.info(f"加载股票-ETF映射，覆盖 {len(self._mapping)} 只股票")

    def save_mapping(self, filepath: str = "data/stock_etf_mapping.json") -> None:
        """保存股票-ETF映射关系"""
        if self._mapping:
            self._holder_provider.save_mapping(self._mapping, filepath)

    def build_mapping(
        self,
        stock_codes: List[str],
        etf_codes: List[str]
    ) -> None:
        """
        构建股票-ETF映射关系

        Args:
            stock_codes: 股票代码列表
            etf_codes: ETF代码列表
        """
        logger.info("开始构建股票-ETF映射关系...")
        self._mapping = self._holder_provider.build_stock_etf_mapping(
            stock_codes, etf_codes
        )
        logger.info(f"映射构建完成，覆盖 {len(self._mapping)} 只股票")

    def get_all_etf_codes(self) -> List[str]:
        """获取所有相关ETF代码"""
        etf_set = set()
        for etf_list in self._mapping.values():
            for etf in etf_list:
                etf_set.add(etf['etf_code'])
        return list(etf_set)

    def find_eligible_etfs(self, stock_code: str) -> List[ETFReference]:
        """
        找到与股票相关的符合条件的ETF

        策略要求：股票在ETF中的持仓占比必须 >= min_weight

        Args:
            stock_code: 股票代码

        Returns:
            符合条件的ETF列表，按权重降序排序
        """
        normalized_code = self._normalize_code(stock_code)

        # 获取映射中的ETF
        mapped_etfs = self._mapping.get(normalized_code, [])

        if not mapped_etfs:
            logger.debug(f"股票 {normalized_code} 没有预构建的映射")
            return []

        # 获取ETF名称映射
        etf_names = {e['etf_code']: e['etf_name'] for e in mapped_etfs}

        results = []

        for etf in mapped_etfs:
            etf_code = etf['etf_code']

            # 获取真实持仓权重
            weight_info = self._get_stock_weight(normalized_code, etf_code)

            # 只保留权重符合要求的ETF
            if weight_info['weight'] >= self._min_weight:
                results.append(ETFReference(
                    etf_code=etf_code,
                    etf_name=etf_names.get(etf_code, f'ETF{etf_code}'),
                    weight=weight_info['weight'],
                    category=self._get_etf_category(etf_code),
                    rank=weight_info['rank'],
                    in_top10=weight_info['in_top10'],
                    top10_ratio=weight_info['top10_ratio']
                ))

        # 按权重降序排序
        results.sort(key=lambda x: x.weight, reverse=True)

        if results:
            logger.info(f"{normalized_code} 符合策略的ETF: {len(results)}个")
            for r in results[:3]:
                logger.info(f"  - {r.etf_name}: 权重{r.weight_pct:.2f}%, 排名第{r.rank}")

        return results

    def find_related_etfs(self, stock_code: str) -> List[Dict]:
        """
        找到与股票相关的ETF（用于API展示，不验证权重）

        Args:
            stock_code: 股票代码

        Returns:
            相关ETF列表
        """
        normalized_code = self._normalize_code(stock_code)
        return self._mapping.get(normalized_code, [])

    def _get_stock_weight(self, stock_code: str, etf_code: str) -> Dict:
        """
        获取股票在ETF中的实际权重和排名

        Returns:
            {
                'weight': float,      # 实际权重
                'rank': int,          # 在ETF中的排名
                'in_top10': bool,     # 是否在前10
                'top10_ratio': float  # 前10持仓总占比
            }
        """
        try:
            holdings_data = self._holdings_provider.get_etf_top_holdings(etf_code)

            if not holdings_data or not holdings_data.get('top_holdings'):
                return {'weight': 0, 'rank': -1, 'in_top10': False, 'top10_ratio': 0}

            holdings = holdings_data['top_holdings']

            # 查找股票在持仓中的位置
            rank = -1
            weight = 0
            for i, h in enumerate(holdings):
                if h['stock_code'] == stock_code:
                    rank = i + 1
                    weight = h['weight']
                    break

            return {
                'weight': weight,
                'rank': rank,
                'in_top10': rank > 0 and rank <= 10,
                'top10_ratio': holdings_data.get('total_weight', 0)
            }

        except Exception as e:
            logger.warning(f"获取 {stock_code} 在 {etf_code} 中的权重失败: {e}")
            return {'weight': 0, 'rank': -1, 'in_top10': False, 'top10_ratio': 0}

    @staticmethod
    def _normalize_code(stock_code: str) -> str:
        """标准化股票代码，去掉市场前缀"""
        prefixes = ['sh', 'sz', 'bj']
        code = stock_code.lower()
        for prefix in prefixes:
            if code.startswith(prefix):
                return code[2:]
        return stock_code

    @staticmethod
    def _get_etf_category(etf_code: str) -> ETFCategory:
        """根据ETF代码获取分类"""
        broad_based = ["510300", "510500", "510050", "159915", "588000",
                       "159901", "512100", "588200"]
        tech = ["159995", "512480", "515000", "516160", "515790"]
        consumer = ["512590", "159928", "512170"]
        financial = ["512880", "512800"]

        if etf_code in broad_based:
            return ETFCategory.BROAD_INDEX
        elif etf_code in tech:
            return ETFCategory.TECH
        elif etf_code in consumer:
            return ETFCategory.CONSUMER
        elif etf_code in financial:
            return ETFCategory.FINANCIAL
        else:
            return ETFCategory.OTHER
