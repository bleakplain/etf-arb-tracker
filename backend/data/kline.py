"""
K线图数据获取模块
使用AKShare获取历史行情数据
"""

import akshare as ak
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class KlineDataFetcher:
    """K线数据获取器 - 基于AKShare"""

    def __init__(self):
        self.data_source = 'AKShare'

    def get_kline(self, stock_code: str, period: str = 'daily',
                   count: int = 120) -> List[Dict]:
        """
        获取K线数据

        Args:
            stock_code: 股票代码
            period: 周期 (daily=日k, weekly=周k, monthly=月k)
            count: 获取数量

        Returns:
            K线数据列表
        """
        try:
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=count * 2)  # 多取一些，过滤非交易日

            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')

            # AKShare获取历史行情
            logger.debug(f"正在获取 {stock_code} 的K线数据...")

            # period参数映射
            period_map = {
                'daily': 'daily',
                'weekly': 'weekly',
                'monthly': 'monthly'
            }
            ak_period = period_map.get(period, 'daily')

            # 调用AKShare接口
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period=ak_period,
                start_date=start_str,
                end_date=end_str,
                adjust=''  # 不复权
            )

            if df.empty:
                logger.warning(f"未获取到 {stock_code} 的K线数据")
                return []

            # 转换为标准格式
            klines = []
            for _, row in df.iterrows():
                klines.append({
                    'date': str(row.get('日期', '')),
                    'open': float(row.get('开盘', 0)) or 0,
                    'close': float(row.get('收盘', 0)) or 0,
                    'high': float(row.get('最高', 0)) or 0,
                    'low': float(row.get('最低', 0)) or 0,
                    'volume': int(row.get('成交量', 0)) or 0,  # 手
                    'amount': float(row.get('成交额', 0)) or 0  # 元
                })

            # 取最后count条
            klines = klines[-count:] if len(klines) > count else klines

            logger.info(f"成功获取 {stock_code} 的 {len(klines)} 条K线数据")
            return klines

        except Exception as e:
            logger.error(f"获取K线数据异常 ({stock_code}): {e}")
            return []

    def get_kline_for_chart(self, stock_code: str, days: int = 60) -> Dict:
        """
        获取用于图表展示的K线数据

        Args:
            stock_code: 股票代码
            days: 天数

        Returns:
            图表数据字典
        """
        klines = self.get_kline(stock_code, 'daily', days)

        if not klines:
            logger.warning(f"无法获取 {stock_code} 的K线数据")
            return {}

        # 转换为图表格式
        dates = [k['date'] for k in klines]
        values = [[k['open'], k['close'], k['low'], k['high']] for k in klines]
        volumes = [k['volume'] for k in klines]

        # 计算均线
        closes = [k['close'] for k in klines]
        ma5 = self._calculate_ma(closes, 5)
        ma10 = self._calculate_ma(closes, 10)
        ma20 = self._calculate_ma(closes, 20)

        return {
            'dates': dates,
            'values': values,
            'volumes': volumes,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20
        }

    def _calculate_ma(self, data: List[float], period: int) -> List[Optional[float]]:
        """计算移动平均线"""
        ma = []
        for i in range(len(data)):
            if i < period - 1:
                ma.append(None)
            else:
                avg = sum(data[i - period + 1:i + 1]) / period
                ma.append(round(avg, 2))
        return ma

    def get_etf_kline(self, etf_code: str, days: int = 60) -> Dict:
        """
        获取ETF的K线数据

        Args:
            etf_code: ETF代码
            days: 天数

        Returns:
            K线数据字典
        """
        try:
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days * 2)

            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')

            logger.debug(f"正在获取ETF {etf_code} 的K线数据...")

            # AKShare获取ETF历史行情
            df = ak.fund_etf_hist_em(
                symbol=etf_code,
                period='daily',
                start_date=start_str,
                end_date=end_str,
                adjust=''
            )

            if df.empty:
                logger.warning(f"未获取到ETF {etf_code} 的K线数据")
                return {}

            # 转换为标准格式
            klines = []
            for _, row in df.iterrows():
                klines.append({
                    'date': str(row.get('日期', '')),
                    'open': float(row.get('开盘', 0)) or 0,
                    'close': float(row.get('收盘', 0)) or 0,
                    'high': float(row.get('最高', 0)) or 0,
                    'low': float(row.get('最低', 0)) or 0,
                    'volume': int(row.get('成交量', 0)) or 0,
                    'amount': float(row.get('成交额', 0)) or 0
                })

            # 转换为图表格式
            dates = [k['date'] for k in klines]
            values = [[k['open'], k['close'], k['low'], k['high']] for k in klines]
            volumes = [k['volume'] for k in klines]

            # 计算均线
            closes = [k['close'] for k in klines]
            ma5 = self._calculate_ma(closes, 5)
            ma10 = self._calculate_ma(closes, 10)
            ma20 = self._calculate_ma(closes, 20)

            return {
                'dates': dates,
                'values': values,
                'volumes': volumes,
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20
            }

        except Exception as e:
            logger.error(f"获取ETF K线数据异常 ({etf_code}): {e}")
            return {}

    def get_stock_info(self, stock_code: str) -> Dict:
        """
        获取股票基本信息

        Args:
            stock_code: 股票代码

        Returns:
            股票基本信息
        """
        try:
            # AKShare获取个股信息
            info = ak.stock_individual_info_em(symbol=stock_code)

            if info.empty:
                return {}

            result = {}
            for _, row in info.iterrows():
                key = str(row.get('item', ''))
                value = str(row.get('value', ''))
                result[key] = value

            return result

        except Exception as e:
            logger.error(f"获取股票信息失败 ({stock_code}): {e}")
            return {}


# 测试代码
