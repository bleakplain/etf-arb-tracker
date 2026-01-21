"""
涨停股数据获取模块
使用数据管理器获取当日所有涨停股票
优化：复用StockQuoteFetcher的缓存数据
"""

import pandas as pd
from typing import List, Dict
from datetime import datetime
from loguru import logger


def _safe_float(value, default=0.0):
    """安全地转换为float，处理'-'等无效值"""
    try:
        if value is None or value == '' or value == '-':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default=0):
    """安全地转换为int，处理'-'等无效值"""
    try:
        if value is None or value == '' or value == '-':
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


class LimitUpStocksFetcher:
    """涨停股票数据获取器 - 复用股票行情缓存"""

    def __init__(self):
        self.data_source = 'DataManager'
        self._data_manager = None

    def _get_data_manager(self):
        """获取数据管理器"""
        if self._data_manager is None:
            from backend.data.data_manager import get_data_manager
            self._data_manager = get_data_manager()
        return self._data_manager

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
            # 如果没有传入数据，获取数据
            if stock_df is None or stock_df.empty:
                logger.info("正在获取涨停股票数据...")
                data_manager = self._get_data_manager()
                stock_df = data_manager.fetch_stock_spot()

                if stock_df.empty:
                    logger.error("获取A股行情数据失败")
                    return []
            else:
                logger.debug(f"复用缓存数据，包含 {len(stock_df)} 只股票")

            # 使用pandas向量化操作筛选涨停股
            mask = stock_df.apply(
                lambda row: self._is_limit_up(
                    str(row.get('代码', '')),
                    _safe_float(row.get('涨跌幅'))
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
            price = _safe_float(row.get('最新价'))
            change_pct = _safe_float(row.get('涨跌幅'))
            open_price = _safe_float(row.get('今开'))
            high = _safe_float(row.get('最高'))
            low = _safe_float(row.get('最低'))
            volume = _safe_int(row.get('成交量'))  # 手
            amount = _safe_float(row.get('成交额'))  # 元
            turnover = _safe_float(row.get('换手率')) if '换手率' in row else 0.0

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

    def _is_limit_up(self, code: str, change_pct: float) -> bool:
        """
        判断是否涨停

        Args:
            code: 股票代码
            change_pct: 涨跌幅（小数形式，如0.0995表示9.95%）

        Returns:
            是否涨停
        """
        # change_pct 使用小数形式，如 0.095 表示 9.5%
        if change_pct < 0.095:
            return False

        if code.startswith('688') or code.startswith('300'):
            return change_pct >= 0.195
        elif code.startswith('8') or code.startswith('4'):
            return change_pct >= 0.295
        else:
            return change_pct >= 0.095

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
