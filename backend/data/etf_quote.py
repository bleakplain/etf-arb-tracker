"""
ETF行情数据获取模块
"""

from .stock_quote import StockQuoteFetcher
from loguru import logger
from typing import Dict, List


class ETFQuoteFetcher(StockQuoteFetcher):
    """ETF行情获取器，继承自StockQuoteFetcher"""

    def __init__(self):
        super().__init__()
        # ETF通常的涨跌停限制与股票不同
        self.etf_limits = {
            'default': 0.10,  # 普通ETF 10%
            'bond': 0.10,     # 债券ETF 10%
            'gold': 0.10,     # 黄金ETF 10%
            'cross': 0.10,    # 跨境ETF 10%
            'commodity': 0.10  # 商品ETF 10%
        }

    def get_etf_quote(self, etf_code: str) -> Dict:
        """
        获取ETF实时行情

        Args:
            etf_code: ETF代码

        Returns:
            ETF行情数据字典
        """
        quote = self.get_stock_quote(etf_code)

        if quote:
            # 添加ETF特有字段
            quote['asset_type'] = 'ETF'
            # ETF通常有IOPV（实时参考净值）
            quote['iopv'] = self._get_iopv(etf_code)
            # 溢价率
            if quote['iopv'] > 0:
                quote['premium'] = (quote['price'] / quote['iopv'] - 1) * 100
            else:
                quote['premium'] = None

        return quote

    def _get_iopv(self, etf_code: str) -> float:
        """
        获取ETF的IOPV（Indicative Optimized Portfolio Value）
        实时参考净值，用于计算溢价折价

        注意：这通常需要专门的数据源，这里简化处理
        """
        # TODO: 实现IOPV获取
        # 可以从交易所网站或专门的金融数据API获取
        return 0.0

    def get_etf_batch_quotes(self, etf_codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取ETF行情

        Args:
            etf_codes: ETF代码列表

        Returns:
            {ETF代码: 行情数据}
        """
        quotes = self.get_batch_quotes(etf_codes)

        # 添加ETF特有信息
        for code in quotes:
            quotes[code]['asset_type'] = 'ETF'
            quotes[code]['iopv'] = self._get_iopv(code)
            if quotes[code]['iopv'] > 0:
                quotes[code]['premium'] = (quotes[code]['price'] /
                                          quotes[code]['iopv'] - 1) * 100
            else:
                quotes[code]['premium'] = None

        return quotes

    def check_liquidity(self, etf_code: str, min_amount: float = 50000000) -> bool:
        """
        检查ETF流动性

        Args:
            etf_code: ETF代码
            min_amount: 最小日成交额要求（元），默认5000万

        Returns:
            是否满足流动性要求
        """
        quote = self.get_etf_quote(etf_code)

        if not quote:
            return False

        # 使用当前成交额估算（实际应该用历史日均成交额）
        # 这里简化处理，实际应该从历史数据获取
        current_amount = quote.get('amount', 0)

        # 估算日成交额（当前成交额 / 交易时长 * 4小时）
        # 这只是粗略估算
        return current_amount >= min_amount / 4  # 保守估计


# 测试代码
if __name__ == "__main__":
    fetcher = ETFQuoteFetcher()

    # 测试获取ETF行情
    etf_codes = ["510300", "510500", "159915", "588000"]

    print("=== ETF行情测试 ===")
    quotes = fetcher.get_etf_batch_quotes(etf_codes)

    for code, quote in quotes.items():
        print(f"\n{quote['name']} ({code}):")
        print(f"  价格: {quote['price']:.3f}")
        print(f"  涨跌幅: {quote['change_pct']:+.2f}%")
        if quote['premium'] is not None:
            print(f"  溢价率: {quote['premium']:+.2f}%")
        print(f"  成交额: {quote['amount']/100000000:.2f}亿")

    # 测试流动性检查
    print("\n=== 流动性检查 ===")
    for code in etf_codes:
        is_liquid = fetcher.check_liquidity(code, min_amount=50000000)
        print(f"{code}: {'✓ 流动性良好' if is_liquid else '✗ 流动性不足'}")
