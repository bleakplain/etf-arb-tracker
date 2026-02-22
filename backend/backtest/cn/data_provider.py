"""
回测数据提供者 - 简化版

同时实现 IQuoteFetcher 和 IETFHoldingProvider 接口，
为回测提供历史行情和持仓数据。
"""

import random
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from backend.market.interfaces import IQuoteFetcher, IETFHoldingProvider
from backend.market import CandidateETF, ETFCategory


class BacktestDataProvider(IQuoteFetcher, IETFHoldingProvider):
    """
    回测数据提供者（简化版）

    同时实现两个接口：
    - IQuoteFetcher: 提供历史行情数据
    - IETFHoldingProvider: 提供持仓数据（固定或 mock）

    数据格式：
    - quotes: {date: {code: quote_dict}}
    - holdings: {stock_code: [CandidateETF, ...]}
    """

    # ETF 名称映射
    ETF_NAMES = {
        "510300": "沪深300ETF", "510500": "中证500ETF", "510050": "上证50ETF",
        "159915": "创业板ETF", "588000": "科创50ETF", "159901": "深100ETF",
        "512100": "中证1000ETF", "588200": "科创100ETF", "512480": "半导体ETF",
        "515000": "5GETF", "516160": "新能源ETF", "515790": "光伏ETF",
        "512590": "医药ETF", "159928": "消费ETF", "512170": "医疗ETF",
        "512880": "证券ETF", "512800": "银行ETF"
    }

    def __init__(
        self,
        quotes: Dict[str, Dict[str, dict]],
        holdings: Optional[Dict[str, List[CandidateETF]]] = None,
        etf_codes: Optional[List[str]] = None,
        use_mock_holdings: bool = True,
        mock_etf_count: int = 4
    ):
        """
        初始化数据提供者

        Args:
            quotes: 历史行情数据 {date: {code: quote_dict}}
            holdings: 持仓数据 {stock_code: [CandidateETF, ...]}（可选）
            etf_codes: ETF 代码列表（用于 mock 数据）
            use_mock_holdings: 是否使用 mock 持仓数据
            mock_etf_count: 每只股票随机关联的 ETF 数量
        """
        self.quotes = quotes  # {"20240102": {"600519": {...}, ...}}
        self.holdings = holdings or {}
        self.etf_codes = etf_codes or []
        self.use_mock_holdings = use_mock_holdings
        self.mock_etf_count = min(mock_etf_count, len(etf_codes)) if etf_codes else 4

        self.current_date: Optional[str] = None

        # 如果使用 mock 且没有持仓数据，生成 mock 数据
        if use_mock_holdings and not self.holdings and etf_codes:
            self._generate_mock_holdings()

        logger.info(
            f"回测数据提供者初始化: {len(self.quotes)}个交易日, "
            f"{len(self.holdings)}只股票有持仓数据"
        )

    def _generate_mock_holdings(self) -> None:
        """生成 mock 持仓数据"""
        # 从所有日期中提取股票代码
        stock_codes = set()
        for daily_quotes in self.quotes.values():
            stock_codes.update(daily_quotes.keys())

        for stock_code in stock_codes:
            # 随机选择 ETF
            if len(self.etf_codes) <= self.mock_etf_count:
                selected_etfs = self.etf_codes
            else:
                selected_etfs = random.sample(self.etf_codes, self.mock_etf_count)

            # 随机分配权重
            remaining_weight = 0.40  # 总权重 40%
            etf_list = []

            for i, etf_code in enumerate(selected_etfs):
                if i == len(selected_etfs) - 1:
                    weight = remaining_weight
                else:
                    max_weight = min(0.15, remaining_weight / (len(selected_etfs) - i))
                    weight = random.uniform(0.05, max_weight)
                    remaining_weight -= weight

                etf_list.append(CandidateETF(
                    etf_code=etf_code,
                    etf_name=self.ETF_NAMES.get(etf_code, f"ETF{etf_code}"),
                    weight=round(weight, 4),
                    category=self._get_etf_category(etf_code),
                    rank=i + 1,
                    in_top10=i < 3,
                    top10_ratio=round(weight * (1 + random.uniform(0, 0.2)), 4)
                ))

            self.holdings[stock_code] = sorted(etf_list, key=lambda x: x.weight, reverse=True)

        logger.info(f"生成 mock 持仓数据: {len(self.holdings)} 只股票")

    @staticmethod
    def _get_etf_category(etf_code: str) -> ETFCategory:
        """根据 ETF 代码获取分类"""
        # 宽基指数
        broad_index = ["510300", "510500", "510050", "159915", "588000",
                       "159901", "512100", "588200"]
        # 行业/主题
        sector = ["159995", "512480", "515000", "516160", "515790",
                  "512590", "159928", "512170", "512880", "512800"]

        if etf_code in broad_index:
            return ETFCategory.BROAD_INDEX
        elif etf_code in sector:
            return ETFCategory.SECTOR
        else:
            return ETFCategory.OTHER

    # ========== IQuoteFetcher 接口 ==========

    def set_current_date(self, date: str) -> None:
        """
        设置当前日期

        Args:
            date: 日期字符串 "YYYYMMDD"
        """
        self.current_date = date

    def get_stock_quote(self, code: str) -> Optional[Dict]:
        """获取股票行情（当前日期）"""
        if not self.current_date:
            raise RuntimeError("未设置当前日期，请先调用 set_current_date()")

        return self.quotes.get(self.current_date, {}).get(code)

    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取股票行情"""
        return {code: self.get_stock_quote(code) for code in codes}

    def is_trading_time(self) -> bool:
        """判断是否交易时间（简化：总是返回 True）"""
        return True

    # ========== IETFHoldingProvider 接口 ==========

    def get_etf_top_holdings(self, etf_code: str) -> Optional[Dict]:
        """
        获取 ETF 前十大持仓

        简化版：返回空数据
        回测主要使用"哪些 ETF 持有某只股票"的反向查询
        """
        return {"top_holdings": [], "total_weight": 0}

    def get_etfs_holding_stock(self, stock_code: str) -> List[CandidateETF]:
        """
        获取持有指定股票的 ETF 列表

        这是回测的核心查询方法

        Args:
            stock_code: 股票代码

        Returns:
            ETF 列表，按权重降序排列
        """
        return self.holdings.get(stock_code, [])

    def load_mapping(self, filepath: str) -> Optional[Dict]:
        """加载映射文件（不适用）"""
        return None

    def save_mapping(self, mapping: Dict, filepath: str) -> None:
        """保存映射文件（不适用）"""
        pass

    def build_stock_etf_mapping(self, stock_codes: List[str], etf_codes: List[str]) -> Dict:
        """构建映射（不适用）"""
        return {}

    # ========== 辅助方法 ==========

    def get_available_dates(self) -> List[str]:
        """获取可用的交易日期列表"""
        return sorted(self.quotes.keys())

    def get_data_summary(self) -> Dict:
        """获取数据摘要"""
        return {
            "dates_count": len(self.quotes),
            "stocks_with_holdings": len(self.holdings),
            "using_mock_holdings": self.use_mock_holdings,
            "date_range": f"{min(self.quotes.keys())} ~ {max(self.quotes.keys())}" if self.quotes else "N/A"
        }
