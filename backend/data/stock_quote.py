"""
A股实时行情数据获取模块
支持从新浪、腾讯等数据源获取实时行情
"""

import requests
import pandas as pd
import re
import time
from typing import Dict, List, Optional
from datetime import datetime, time as dt_time
from loguru import logger


class StockQuoteFetcher:
    """A股行情数据获取器"""

    def __init__(self):
        self.sources = {
            'sina': 'http://hq.sinajs.cn/list=',
            'tencent': 'http://qt.gtimg.cn/q='
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn'
        }

    def get_stock_quote(self, stock_code: str, source: str = 'sina') -> Optional[Dict]:
        """
        获取单只股票的实时行情

        Args:
            stock_code: 股票代码（6位数字）
            source: 数据源 ('sina' 或 'tencent')

        Returns:
            {
                'code': '股票代码',
                'name': '股票名称',
                'price': 当前价,
                'prev_close': 昨收,
                'open': 开盘价,
                'high': 最高价,
                'low': 最低价,
                'volume': 成交量(手),
                'amount': 成交额(元),
                'change': 涨跌额,
                'change_pct': 涨跌幅,
                'is_limit_up': 是否涨停,
                'is_limit_down': 是否跌停,
                'timestamp': 时间戳
            }
        """
        # 构造完整的股票代码（加上市场前缀）
        full_code = self._format_code(stock_code)

        try:
            if source == 'sina':
                return self._get_from_sina(full_code)
            elif source == 'tencent':
                return self._get_from_tencent(full_code)
            else:
                logger.error(f"不支持的数据源: {source}")
                return None

        except Exception as e:
            logger.error(f"获取股票 {stock_code} 行情失败: {e}")
            return None

    def _format_code(self, stock_code: str) -> str:
        """
        格式化股票代码，添加市场前缀

        Args:
            stock_code: 6位股票代码

        Returns:
            带前缀的代码，如 sh600519 或 sz300750
        """
        # 根据代码判断市场
        if stock_code.startswith('6'):
            return f"sh{stock_code}"  # 上海
        elif stock_code.startswith(('0', '3')):
            return f"sz{stock_code}"  # 深圳
        elif stock_code.startswith('8') or stock_code.startswith('4'):
            return f"bj{stock_code}"  # 北京
        else:
            # 如果已经有前缀，直接返回
            if stock_code[:2] in ['sh', 'sz', 'bj']:
                return stock_code
            return stock_code

    def _get_from_sina(self, full_code: str) -> Optional[Dict]:
        """从新浪财经获取行情数据"""

        url = f"{self.sources['sina']}{full_code}"
        response = requests.get(url, headers=self.headers, timeout=5)
        response.encoding = 'gbk'

        if response.status_code != 200:
            return None

        # 解析返回的数据
        # 格式: var hq_str_sh600519="贵州茅台,1675.00,1660.00,..."
        text = response.text
        match = re.search(f'hq_str_{full_code}="([^"]*)"', text)

        if not match:
            return None

        data_str = match.group(1)
        if not data_str:
            return None

        fields = data_str.split(',')

        # 新浪数据格式说明（共32个字段）:
        # 0:名称 1:开盘 2:昨收 3:当前价 4:最高 5:最低
        # 6:买一 7:卖一 8:成交量(手) 9:成交额(元)
        # 10:买一量 11:买一价 12:买二量 13:买二价 ...
        # 30:日期 31:时间

        if len(fields) < 31:
            return None

        try:
            name = fields[0]
            open_price = float(fields[1]) if fields[1] else 0
            prev_close = float(fields[2]) if fields[2] else 0
            current_price = float(fields[3]) if fields[3] else 0
            high = float(fields[4]) if fields[4] else 0
            low = float(fields[5]) if fields[5] else 0
            volume = int(fields[8]) if fields[8] else 0  # 手
            amount = float(fields[9]) if fields[9] else 0  # 元
            date_str = fields[30]
            time_str = fields[31]

            # 如果当前价为0（未开盘或停牌），使用昨收价代替
            if current_price == 0 and prev_close > 0:
                current_price = prev_close
                change = 0
                change_pct = 0
            else:
                # 计算涨跌
                change = current_price - prev_close
                change_pct = (change / prev_close * 100) if prev_close > 0 else 0

            # 判断是否涨停
            is_limit_up = self._is_limit_up(full_code, current_price, prev_close)

            return {
                'code': full_code[2:],  # 去掉前缀
                'name': name,
                'price': current_price,
                'prev_close': prev_close,
                'open': open_price,
                'high': high,
                'low': low,
                'volume': volume,
                'amount': amount,
                'change': change,
                'change_pct': change_pct,
                'is_limit_up': is_limit_up,
                'is_limit_down': False,  # 可扩展
                'timestamp': f"{date_str} {time_str}",
                'data_source': 'sina'
            }

        except (ValueError, IndexError) as e:
            logger.error(f"解析新浪数据失败: {e}")
            return None

    def _get_from_tencent(self, full_code: str) -> Optional[Dict]:
        """从腾讯财经获取行情数据"""

        url = f"{self.sources['tencent']}{full_code}"
        response = requests.get(url, headers=self.headers, timeout=5)

        if response.status_code != 200:
            return None

        # 腾讯数据格式: v_sh600519="51~贵州茅台~1675.00~..."
        text = response.text
        match = re.search(f'v_{full_code}="([^"]*)"', text)

        if not match:
            return None

        data_str = match.group(1)
        fields = data_str.split('~')

        # 解析字段（根据腾讯API文档）
        if len(fields) < 50:
            return None

        try:
            name = fields[1]
            current_price = float(fields[3]) if fields[3] else 0
            prev_close = float(fields[4]) if fields[4] else 0
            open_price = float(fields[5]) if fields[5] else 0
            volume = int(fields[6]) if fields[6] else 0
            high = float(fields[33]) if fields[33] else 0
            low = float(fields[34]) if fields[34] else 0
            amount = float(fields[37]) if fields[37] else 0

            change = current_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close > 0 else 0

            is_limit_up = self._is_limit_up(full_code, current_price, prev_close)

            return {
                'code': full_code[2:],
                'name': name,
                'price': current_price,
                'prev_close': prev_close,
                'open': open_price,
                'high': high,
                'low': low,
                'volume': volume,
                'amount': amount,
                'change': change,
                'change_pct': change_pct,
                'is_limit_up': is_limit_up,
                'is_limit_down': False,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'data_source': 'tencent'
            }

        except (ValueError, IndexError) as e:
            logger.error(f"解析腾讯数据失败: {e}")
            return None

    def _is_limit_up(self, full_code: str, current_price: float,
                     prev_close: float) -> bool:
        """
        判断是否涨停

        A股涨跌停规则:
        - 主板(60xxxx, 00xxxx): ±10%
        - 科创板/创业板(30xxxx, 688xxx): ±20%
        - 北交所/ST股票: ±5%
        """
        if prev_close == 0:
            return False

        change_pct = (current_price - prev_close) / prev_close

        # 判断股票类型
        code = full_code[2:]

        if code.startswith('688') or code.startswith('300'):
            limit = 0.20  # 科创板/创业板 20%
        elif code.startswith('8') or code.startswith('4'):
            limit = 0.30  # 北交所 30%
        else:
            limit = 0.10  # 主板 10%

        # 允许一点误差（四舍五入）
        return change_pct >= (limit - 0.001)

    def get_batch_quotes(self, stock_codes: List[str],
                          source: str = 'sina') -> Dict[str, Dict]:
        """
        批量获取多只股票行情

        Args:
            stock_codes: 股票代码列表
            source: 数据源

        Returns:
            {股票代码: 行情数据}
        """
        results = {}

        # 批量请求（每次最多50只）
        batch_size = 50
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i + batch_size]
            codes_str = ','.join([self._format_code(c) for c in batch])

            try:
                if source == 'sina':
                    results.update(self._batch_get_sina(codes_str))
                elif source == 'tencent':
                    results.update(self._batch_get_tencent(codes_str))

                time.sleep(0.1)  # 避免请求过快

            except Exception as e:
                logger.error(f"批量获取失败: {e}")

        return results

    def _batch_get_sina(self, codes_str: str) -> Dict[str, Dict]:
        """新浪批量获取"""
        url = f"{self.sources['sina']}{codes_str}"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.encoding = 'gbk'

        results = {}

        # 新浪返回多行数据
        for line in response.text.strip().split('\n'):
            match = re.search(r'hq_str_(sh|sz|bj)(\d{6})="([^"]*)"', line)
            if match:
                market = match.group(1)
                code = match.group(2)
                full_code = f"{market}{code}"
                data_str = match.group(3)

                if data_str:
                    quote = self._parse_sina_line(full_code, data_str)
                    if quote:
                        results[code] = quote

        return results

    def _parse_sina_line(self, full_code: str, data_str: str) -> Optional[Dict]:
        """解析单行新浪数据"""
        fields = data_str.split(',')

        if len(fields) < 31:
            return None

        try:
            name = fields[0]
            prev_close = float(fields[2]) if fields[2] else 0
            current_price = float(fields[3]) if fields[3] else 0

            # 如果当前价为0（未开盘或停牌），使用昨收价代替
            if current_price == 0 and prev_close > 0:
                current_price = prev_close
                change = 0
                change_pct = 0
            else:
                change = current_price - prev_close
                change_pct = (change / prev_close * 100) if prev_close > 0 else 0

            return {
                'code': full_code[2:],
                'name': name,
                'price': current_price,
                'prev_close': prev_close,
                'change': change,
                'change_pct': change_pct,
                'is_limit_up': self._is_limit_up(full_code, current_price, prev_close),
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except (ValueError, IndexError):
            return None

    def is_trading_time(self) -> bool:
        """判断是否在交易时间内"""
        now = datetime.now().time()

        # 上午: 9:30-11:30
        morning_start = dt_time(9, 30)
        morning_end = dt_time(11, 30)

        # 下午: 13:00-15:00
        afternoon_start = dt_time(13, 0)
        afternoon_end = dt_time(15, 0)

        return (morning_start <= now <= morning_end or
                afternoon_start <= now <= afternoon_end)

    def get_time_to_close(self) -> int:
        """
        获取距离收盘的秒数

        Returns:
            距离15:00收盘的秒数，如果不在交易时间返回-1
        """
        now = datetime.now()
        close_time = now.replace(hour=15, minute=0, second=0, microsecond=0)

        if now.hour < 9 or now.hour >= 15:
            return -1

        delta = close_time - now
        return int(delta.total_seconds())


# 测试代码
if __name__ == "__main__":
    fetcher = StockQuoteFetcher()

    # 测试获取单只股票
    print("\n=== 测试获取贵州茅台行情 ===")
    quote = fetcher.get_stock_quote("600519")
    if quote:
        print(f"股票: {quote['name']} ({quote['code']})")
        print(f"价格: {quote['price']}")
        print(f"涨跌幅: {quote['change_pct']:.2f}%")
        print(f"是否涨停: {quote['is_limit_up']}")

    # 测试批量获取
    print("\n=== 测试批量获取 ===")
    codes = ["600519", "300750", "002594"]
    quotes = fetcher.get_batch_quotes(codes)
    for code, quote in quotes.items():
        print(f"{quote['name']}: {quote['price']:.2f} ({quote['change_pct']:+.2f}%)")

    print(f"\n当前是否交易时间: {fetcher.is_trading_time()}")
    print(f"距离收盘: {fetcher.get_time_to_close()}秒")
