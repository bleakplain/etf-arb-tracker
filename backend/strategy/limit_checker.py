"""
涨停检查器 - 专职检查股票涨停状态
"""

from typing import Optional, Dict, Set
from datetime import datetime
from loguru import logger

from backend.domain.interfaces import IQuoteFetcher
from backend.domain.models import LimitUpInfo


class LimitChecker:
    """
    涨停检查器

    职责：
    1. 检查单只股票是否涨停
    2. 管理已处理的涨停（避免重复）
    """

    def __init__(self, quote_fetcher: IQuoteFetcher):
        """
        初始化涨停检查器

        Args:
            quote_fetcher: 行情数据获取器
        """
        self._quote_fetcher = quote_fetcher
        self._processed_limits: Set[str] = set()

    def check_limit_up(self, stock_code: str) -> Optional[LimitUpInfo]:
        """
        检查单只股票是否涨停

        Args:
            stock_code: 股票代码

        Returns:
            涨停信息，未涨停或已处理返回None
        """
        quote = self._quote_fetcher.get_stock_quote(stock_code)

        if not quote:
            logger.debug(f"未获取到股票 {stock_code} 的行情数据")
            return None

        if not quote.get('is_limit_up', False):
            return None

        # 检查是否已经处理过这个涨停
        limit_key = f"{stock_code}_{datetime.now().strftime('%Y%m%d')}"
        if limit_key in self._processed_limits:
            logger.debug(f"股票 {stock_code} 今天的涨停已处理过")
            return None

        limit_info = LimitUpInfo.from_quote(quote)
        logger.info(f"检测到涨停: {limit_info.stock_name} ({limit_info.stock_code})")

        return limit_info

    def mark_processed(self, stock_code: str) -> None:
        """
        标记涨停为已处理

        Args:
            stock_code: 股票代码
        """
        limit_key = f"{stock_code}_{datetime.now().strftime('%Y%m%d')}"
        self._processed_limits.add(limit_key)
        logger.debug(f"标记涨停已处理: {stock_code}")

    def is_already_processed(self, stock_code: str) -> bool:
        """
        检查涨停是否已处理

        Args:
            stock_code: 股票代码

        Returns:
            是否已处理
        """
        limit_key = f"{stock_code}_{datetime.now().strftime('%Y%m%d')}"
        return limit_key in self._processed_limits

    def clear_processed(self) -> None:
        """清空已处理的涨停记录"""
        self._processed_limits.clear()
        logger.info("已清空涨停处理记录")

    def get_processed_count(self) -> int:
        """获取已处理的涨停数量"""
        return len(self._processed_limits)
