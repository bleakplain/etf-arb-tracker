"""
涨停股数据获取模块
使用东方财富数据源获取当日所有涨停股票
"""

import pandas as pd
from typing import List, Dict
from loguru import logger

from backend.data.utils import safe_float, safe_int, is_limit_up


class LimitUpStocksFetcher:
    """涨停股票数据获取器 - 使用东方财富数据源"""

    def __init__(self):
        self.data_source = 'EastMoney'
        self._eastmoney_source = None

    def _get_eastmoney_source(self):
        """获取东方财富数据源"""
        if self._eastmoney_source is None:
            from backend.data.sources.eastmoney_source import EastMoneyLimitUpSource
            self._eastmoney_source = EastMoneyLimitUpSource()
        return self._eastmoney_source

    def get_today_limit_ups(self, stock_df: pd.DataFrame = None) -> List[Dict]:
        """
        获取今日所有涨停股票

        Args:
            stock_df: 可选，已有的股票行情DataFrame（用于兼容）

        Returns:
            涨停股票列表
        """
        try:
            logger.info("正在从东方财富获取涨停股票数据...")
            source = self._get_eastmoney_source()

            # 获取全市场股票数据（按涨幅排序）
            all_stocks = source.fetch_limit_up_stocks()

            if not all_stocks:
                logger.info("未获取到股票数据")
                return []

            # 筛选涨停股（使用更精确的判断）
            limit_up_stocks = []
            for stock in all_stocks:
                code = stock['code']
                change_pct = stock['change_pct']

                # 使用涨停判断函数
                if is_limit_up(code, change_pct):
                    limit_up_stocks.append(stock)

            logger.info(f"从 {len(all_stocks)} 只股票中筛选出 {len(limit_up_stocks)} 只涨停股")
            return limit_up_stocks

        except Exception as e:
            logger.error(f"获取涨停股异常: {e}")
            return []

    def _parse_limit_up_row(self, row: pd.Series) -> Dict:
        """解析涨停股数据行"""
        try:
            code = str(row.get('代码', ''))
            name = str(row.get('名称', ''))
            price = safe_float(row.get('最新价'))
            change_pct = safe_float(row.get('涨跌幅'))
            open_price = safe_float(row.get('今开'))
            high = safe_float(row.get('最高'))
            low = safe_float(row.get('最低'))
            volume = safe_int(row.get('成交量'))
            amount = safe_float(row.get('成交额'))
            turnover = safe_float(row.get('换手率')) if '换手率' in row else 0.0

            return {
                'code': code,
                'name': name,
                'price': price,
                'change_pct': change_pct,
                'open': open_price,
                'high': high,
                'low': low,
                'volume': volume,
                'amount': amount,
                'turnover': turnover,
                'limit_time': '',
                'seal_amount': 0,
                'data_source': 'DataManager'
            }

        except (ValueError, TypeError) as e:
            logger.error(f"解析涨停股数据失败: {e}")
            return {}

    def get_limit_ups_by_sector(self, sector: str = None, stock_df: pd.DataFrame = None) -> List[Dict]:
        """
        按板块获取涨停股

        Args:
            sector: 板块代码
            stock_df: 可选，已有的股票行情DataFrame

        Returns:
            该板块的涨停股列表
        """
        all_limit_ups = self.get_today_limit_ups(stock_df)

        if not sector:
            return all_limit_ups

        if sector == 'sh':
            return [s for s in all_limit_ups if s['code'].startswith('6')]
        elif sector == 'sz':
            return [s for s in all_limit_ups if s['code'].startswith(('0', '3'))]
        elif sector == 'cyb':
            return [s for s in all_limit_ups if s['code'].startswith('30')]
        elif sector == 'kcb':
            return [s for s in all_limit_ups if s['code'].startswith('688')]
        else:
            return all_limit_ups


# 测试代码
