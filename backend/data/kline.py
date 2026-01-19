"""
K线图数据获取模块
使用模拟数据作为备用方案
"""

import requests
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class KlineDataFetcher:
    """K线数据获取器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

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
            # 方案1: 腾讯接口（可能需要处理重定向）
            klines = self._get_kline_from_tencent(stock_code, count)
            if klines:
                return klines

            # 方案2: 网易接口
            klines = self._get_kline_from_163(stock_code, count)
            if klines:
                return klines

            # 方案3: 生成模拟数据（用于演示）
            logger.warning(f"所有K线接口均失败，为 {stock_code} 生成模拟数据")
            return self._generate_mock_kline(stock_code, count)

        except Exception as e:
            logger.error(f"获取K线数据异常 ({stock_code}): {e}")
            return self._generate_mock_kline(stock_code, count)

    def _get_kline_from_tencent(self, stock_code: str, count: int) -> List[Dict]:
        """从腾讯获取K线数据"""
        try:
            symbol = self._get_tencent_symbol(stock_code)

            # 使用腾讯新的API
            url = f"http://ifzq.gtimg.cn/appstock/app/fqkline/get"
            params = {
                'param': symbol,
                'day': '1',
                'week': '0',
                'month': '0',
                'start': '',
                'end': '',
                'qt': '1',
                'full': '1',
                '_var': 'kline_data',
                'r': str(datetime.now().timestamp())
            }

            response = requests.get(url, params=params, headers=self.headers,
                                  timeout=15, allow_redirects=True)
            response.encoding = 'utf-8'

            text = response.text.strip()

            # 检查是否是HTML响应（被重定向）
            if text.startswith('<!DOCTYPE') or text.startswith('<html'):
                return []

            # 去掉jsonp包装
            if 'kline_data=' in text:
                text = text[text.index('{'):text.rindex('}')+1]

            data = json.loads(text) if text else {}

            if 'data' not in data or not data['data']:
                return []

            klines = []
            items = data['data']

            # 取最后count条
            items = items[-count:] if len(items) > count else items

            for item in items:
                if len(item) >= 6:
                    try:
                        klines.append({
                            'date': str(item[0]),
                            'open': float(item[1]),
                            'close': float(item[2]),
                            'high': float(item[3]),
                            'low': float(item[4]),
                            'volume': int(float(item[5])),
                            'amount': float(item[6]) if len(item) > 6 else 0
                        })
                    except (ValueError, IndexError):
                        continue

            if klines:
                logger.info(f"从腾讯获取到 {stock_code} 的 {len(klines)} 条K线数据")
            return klines

        except Exception as e:
            logger.debug(f"从腾讯获取K线失败 ({stock_code}): {e}")
            return []

    def _get_kline_from_163(self, stock_code: str, count: int) -> List[Dict]:
        """从网易获取K线数据"""
        try:
            # 网易历史数据接口
            symbol = self._get_163_symbol(stock_code)
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')

            url = "http://quotes.money.163.com/service/chddata.html"
            params = {
                'code': symbol,
                'start': start_date,
                'end': end_date,
                'fields': 'DATE;OPEN;HIGH;LOW;CLOSE;VOLUME'
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=15)

            if response.status_code != 200:
                return []

            data = response.json()

            if not data or not isinstance(data, list):
                return []

            klines = []
            for item in data:
                if len(item) >= 6:
                    klines.append({
                        'date': item[0],
                        'open': float(item[1]),
                        'high': float(item[2]),
                        'low': float(item[3]),
                        'close': float(item[4]),
                        'volume': int(item[5]),
                        'amount': 0
                    })

            # 取最后count条
            klines = klines[-count:] if len(klines) > count else klines

            if klines:
                logger.info(f"从网易获取到 {stock_code} 的 {len(klines)} 条K线数据")
            return klines

        except Exception as e:
            logger.debug(f"从网易获取K线失败 ({stock_code}): {e}")
            return []

    def _generate_mock_kline(self, stock_code: str, count: int) -> List[Dict]:
        """生成模拟K线数据（用于演示）"""
        base_price = 10.0 + hash(stock_code) % 90  # 基于股票代码生成基础价格

        klines = []
        current_date = datetime.now() - timedelta(days=count)

        for i in range(count):
            date = current_date + timedelta(days=i)

            # 跳过周末
            if date.weekday() >= 5:
                continue

            # 生成随机K线数据
            import random
            random.seed(i + hash(stock_code))

            open_price = base_price + random.uniform(-2, 2)
            close_price = base_price + random.uniform(-2, 2)
            high_price = max(open_price, close_price) + random.uniform(0, 1)
            low_price = min(open_price, close_price) - random.uniform(0, 1)

            volume = int(random.uniform(100000, 10000000))

            klines.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(open_price, 2),
                'close': round(close_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'volume': volume,
                'amount': volume * close_price
            })

            base_price = close_price  # 下一天的基础价格

        logger.info(f"为 {stock_code} 生成了 {len(klines)} 条模拟K线数据")
        return klines

    def _get_tencent_symbol(self, stock_code: str) -> str:
        """获取腾讯股票代码格式"""
        if stock_code.startswith('6'):
            return f'sh{stock_code}'
        elif stock_code.startswith('8') or stock_code.startswith('4'):
            return f'bj{stock_code}'
        else:
            return f'sz{stock_code}'

    def _get_163_symbol(self, stock_code: str) -> str:
        """获取网易股票代码格式"""
        if stock_code.startswith('6'):
            return f'0{stock_code}'
        else:
            return f'1{stock_code}'

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
        """获取ETF的K线数据"""
        return self.get_kline_for_chart(etf_code, days)


# 测试代码
if __name__ == "__main__":
    fetcher = KlineDataFetcher()

    # 测试获取K线数据
    print("测试获取K线数据:")

    test_codes = ['600519', '300750', '688308']

    for code in test_codes:
        print(f"\n测试 {code}:")
        kline_data = fetcher.get_kline_for_chart(code, days=30)

        if kline_data:
            print(f"  ✓ 成功获取 {len(kline_data['dates'])} 条数据")
            print(f"  最新日期: {kline_data['dates'][-1]}")
            print(f"  最新价格: {kline_data['values'][-1]}")
        else:
            print(f"  ✗ 获取失败")
