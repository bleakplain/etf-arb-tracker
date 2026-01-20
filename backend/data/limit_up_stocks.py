"""
涨停股数据获取模块
使用AKShare获取当日所有涨停股票
优化：复用StockQuoteFetcher的缓存数据
"""

import akshare as ak
import pandas as pd
from typing import List, Dict
from datetime import datetime
from loguru import logger


class LimitUpStocksFetcher:
    """涨停股票数据获取器 - 复用股票行情缓存"""

    def __init__(self):
        self.data_source = 'AKShare'

    def get_today_limit_ups(self, stock_df: pd.DataFrame = None) -> List[Dict]:
        """
        获取今日所有涨停股票

        优化：传入已有的股票行情DataFrame，避免重复获取数据

        Args:
            stock_df: 可选，已有的股票行情DataFrame（从StockQuoteFetcher缓存获取）

        Returns:
            涨停股票列表
        """
        try:
            # 如果没有传入数据，才去获取
            if stock_df is None or stock_df.empty:
                logger.info("正在从AKShare获取涨停股票数据...")
                stock_df = ak.stock_zh_a_spot_em()

                if stock_df.empty:
                    logger.error("获取A股行情数据失败")
                    return []
            else:
                logger.debug(f"复用缓存数据，包含 {len(stock_df)} 只股票")

            # 使用pandas向量化操作筛选涨停股（比循环快）
            mask = stock_df.apply(
                lambda row: self._is_limit_up(
                    str(row.get('代码', '')),
                    float(row.get('涨跌幅', 0)) or 0
                ),
                axis=1
            )

            limit_up_df = stock_df[mask]

            # 转换为字典列表
            limit_up_stocks = []
            for _, row in limit_up_df.iterrows():
                parsed = self._parse_limit_up_row(row)
                if parsed:
                    limit_up_stocks.append(parsed)

            logger.info(f"从 {len(stock_df)} 只股票中筛选出 {len(limit_up_stocks)} 只涨停股")
            return limit_up_stocks

        except Exception as e:
            logger.error(f"获取涨停股异常: {e}")
            return []

    def _parse_limit_up_row(self, row: pd.Series) -> Dict:
        """解析涨停股数据行"""
        try:
            code = str(row.get('代码', ''))
            name = str(row.get('名称', ''))
            price = float(row.get('最新价', 0)) or 0
            change_pct = float(row.get('涨跌幅', 0)) or 0
            open_price = float(row.get('今开', 0)) or 0
            high = float(row.get('最高', 0)) or 0
            low = float(row.get('最低', 0)) or 0
            volume = int(float(row.get('成交量', 0))) or 0  # 手
            amount = float(row.get('成交额', 0)) or 0  # 元
            turnover = float(row.get('换手率', 0)) or 0  # %

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
                'data_source': 'AKShare'
            }

        except (ValueError, TypeError) as e:
            logger.error(f"解析涨停股数据失败: {e}")
            return {}

    def _is_limit_up(self, code: str, change_pct: float) -> bool:
        """
        判断是否涨停

        Args:
            code: 股票代码
            change_pct: 涨跌幅（百分比形式，如9.95表示9.95%）

        Returns:
            是否涨停
        """
        if change_pct < 9.5:
            return False

        if code.startswith('688') or code.startswith('300'):
            return change_pct >= 19.5
        elif code.startswith('8') or code.startswith('4'):
            return change_pct >= 29.5
        elif code.startswith('30'):
            return change_pct >= 19.5
        elif code.startswith('6') or code.startswith('00') or code.startswith('60'):
            return change_pct >= 9.5
        else:
            return change_pct >= 9.5

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

    def get_hot_concepts(self) -> List[Dict]:
        """获取当日热门概念板块"""
        try:
            concept_df = ak.stock_board_concept_name_em()

            if concept_df.empty:
                return []

            hot_concepts = []
            for _, row in concept_df.head(50).iterrows():
                hot_concepts.append({
                    'code': str(row.get('板块代码', '')),
                    'name': str(row.get('板块名称', '')),
                    'change_pct': float(row.get('涨跌幅', 0)) or 0,
                    'lead_stock': str(row.get('领涨股票', '')) if '领涨股票' in row else '',
                    'data_source': 'AKShare'
                })

            return hot_concepts

        except Exception as e:
            logger.error(f"获取热门概念失败: {e}")
            return []

    def get_industry_performance(self) -> List[Dict]:
        """获取行业板块表现"""
        try:
            industry_df = ak.stock_board_industry_name_em()

            if industry_df.empty:
                return []

            industries = []
            for _, row in industry_df.iterrows():
                industries.append({
                    'code': str(row.get('板块代码', '')),
                    'name': str(row.get('板块名称', '')),
                    'change_pct': float(row.get('涨跌幅', 0)) or 0,
                    'lead_stock': str(row.get('领涨股票', '')) if '领涨股票' in row else '',
                    'data_source': 'AKShare'
                })

            return industries

        except Exception as e:
            logger.error(f"获取行业板块表现失败: {e}")
            return []


# 测试代码
if __name__ == "__main__":
    fetcher = LimitUpStocksFetcher()

    print("=" * 60)
    print("获取今日涨停股")
    print("=" * 60)

    limit_ups = fetcher.get_today_limit_ups()

    print(f"\n今日涨停股数量: {len(limit_ups)}")

    if limit_ups:
        print("\n前20只涨停股:")
        for i, stock in enumerate(limit_ups[:20], 1):
            print(f"{i}. {stock['name']} ({stock['code']}) - "
                  f"¥{stock['price']:.2f} (+{stock['change_pct']:.2f}%)")
    else:
        print("\n当前无涨停股或非交易时间")
