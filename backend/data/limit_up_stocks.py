"""
涨停股数据获取模块
使用AKShare获取当日所有涨停股票
"""

import akshare as ak
import pandas as pd
from typing import List, Dict
from datetime import datetime
from loguru import logger


class LimitUpStocksFetcher:
    """涨停股票数据获取器 - 基于AKShare"""

    def __init__(self):
        self.data_source = 'AKShare'

    def get_today_limit_ups(self) -> List[Dict]:
        """
        获取今日所有涨停股票

        使用AKShare获取A股实时行情，筛选涨停股

        Returns:
            [
                {
                    'code': '股票代码',
                    'name': '股票名称',
                    'price': 涨停价格,
                    'change_pct': 涨跌幅,
                    'open': 开盘价,
                    'high': 最高价,
                    'low': 最低价,
                    'volume': 成交量(手),
                    'amount': 成交额(元),
                    'turnover': 换手率,
                    'limit_time': 封板时间,
                    'seal_amount': 封单金额
                },
                ...
            ]
        """
        try:
            logger.info("正在从AKShare获取涨停股票数据...")

            # 获取沪深A股实时行情
            stock_df = ak.stock_zh_a_spot_em()

            if stock_df.empty:
                logger.error("获取A股行情数据失败")
                return []

            # 筛选涨停股
            limit_up_stocks = []

            for _, row in stock_df.iterrows():
                code = str(row.get('代码', ''))
                change_pct = float(row.get('涨跌幅', 0)) or 0

                # 判断是否涨停
                if self._is_limit_up(code, change_pct):
                    limit_up_stocks.append(self._parse_limit_up_row(row))

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
                'limit_time': '',  # AKShare暂不提供封板时间
                'seal_amount': 0,   # AKShare暂不提供封单金额
                'data_source': 'AKShare'
            }

        except (ValueError, TypeError) as e:
            logger.error(f"解析涨停股数据失败: {e}")
            return {}

    def _is_limit_up(self, code: str, change_pct: float) -> bool:
        """
        判断是否涨停（严格判断）

        Args:
            code: 股票代码
            change_pct: 涨跌幅（百分比形式，如9.95表示9.95%）

        Returns:
            是否涨停
        """
        if change_pct < 9.5:  # 涨幅小于9.5%，肯定不是涨停
            return False

        # 根据板块判断涨停限制
        if code.startswith('688') or code.startswith('300'):
            # 科创板/创业板: 20%涨停
            # 允许一点误差（四舍五入）
            return change_pct >= 19.5
        elif code.startswith('8') or code.startswith('4'):
            # 北交所: 30%涨停
            return change_pct >= 29.5
        elif code.startswith('30'):
            # 创业板: 20%涨停
            return change_pct >= 19.5
        elif code.startswith('6') or code.startswith('00') or code.startswith('60'):
            # 主板: 10%涨停
            # ST股票是5%，但这里简化处理
            return change_pct >= 9.5
        else:
            # 其他情况，按10%计算
            return change_pct >= 9.5

    def get_limit_ups_by_sector(self, sector: str = None) -> List[Dict]:
        """
        按板块获取涨停股

        Args:
            sector: 板块代码 ('sh'=上海, 'sz'=深圳, 'cyb'=创业板, 'kcb'=科创板)
                   如果为None，返回所有涨停股

        Returns:
            该板块的涨停股列表
        """
        all_limit_ups = self.get_today_limit_ups()

        if not sector:
            return all_limit_ups

        # 根据板块筛选
        if sector == 'sh':
            # 上海市场：60xxxx, 688xxx
            return [s for s in all_limit_ups if s['code'].startswith('6')]
        elif sector == 'sz':
            # 深圳市场：00xxxx, 30xxxx
            return [s for s in all_limit_ups if s['code'].startswith(('0', '3'))]
        elif sector == 'cyb':
            # 创业板：30xxxx
            return [s for s in all_limit_ups if s['code'].startswith('30')]
        elif sector == 'kcb':
            # 科创板：688xxx
            return [s for s in all_limit_ups if s['code'].startswith('688')]
        else:
            return all_limit_ups

    def get_hot_concepts(self) -> List[Dict]:
        """
        获取当日热门概念板块

        Returns:
            [
                {'name': '概念名称', 'code': '概念代码', 'change_pct': 涨幅},
                ...
            ]
        """
        try:
            logger.info("正在从AKShare获取热门概念板块...")

            # AKShare获取概念板块行情
            concept_df = ak.stock_board_concept_name_em()

            if concept_df.empty:
                logger.warning("获取概念板块数据为空")
                return []

            # 按涨幅排序，取前50
            hot_concepts = []
            for _, row in concept_df.head(50).iterrows():
                hot_concepts.append({
                    'code': str(row.get('板块代码', '')),
                    'name': str(row.get('板块名称', '')),
                    'change_pct': float(row.get('涨跌幅', 0)) or 0,
                    'lead_stock': str(row.get('领涨股票', '')) if '领涨股票' in row else '',
                    'data_source': 'AKShare'
                })

            logger.info(f"获取到 {len(hot_concepts)} 个热门概念板块")
            return hot_concepts

        except Exception as e:
            logger.error(f"获取热门概念失败: {e}")
            return []

    def get_industry_performance(self) -> List[Dict]:
        """
        获取行业板块表现

        Returns:
            [{'name': '行业名称', 'change_pct': 涨幅, 'count': 涨停股数量}, ...]
        """
        try:
            # 获取行业板块行情
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

    # 测试热门概念
    print("\n" + "=" * 60)
    print("热门概念板块")
    print("=" * 60)

    concepts = fetcher.get_hot_concepts()
    if concepts:
        print(f"\n前10个热门概念:")
        for i, concept in enumerate(concepts[:10], 1):
            print(f"{i}. {concept['name']} - {concept['change_pct']:+.2f}%")
