"""
东方财富涨停股数据源
专门用于获取全市场涨停股票数据
"""

import requests
import pandas as pd
import time
from typing import List, Dict, Optional
from loguru import logger

from backend.data.source_base import (
    BaseDataSource,
    SourceType,
    DataType,
    SourceCapability
)
from backend.data.utils import safe_float, safe_int


class EastMoneyLimitUpSource(BaseDataSource):
    """
    东方财富涨停股数据源

    特点：
    - 支持全市场涨停股查询
    - 无需token
    - 实时数据
    """

    # 默认请求间隔（秒）- 防止被封禁
    DEFAULT_REQUEST_INTERVAL = 5
    # 最大重试次数
    MAX_RETRIES = 2

    def __init__(self, priority: int = 1, request_interval: Optional[float] = None):
        super().__init__(
            name="eastmoney_limit_up",
            source_type=SourceType.FREE_HIGH_FREQ,
            priority=priority
        )
        self.base_url = 'http://82.push2.eastmoney.com/api/qt/clist/getlist'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://quote.eastmoney.com'
        })
        # 请求间隔，防止被封禁
        self._request_interval = request_interval or self.DEFAULT_REQUEST_INTERVAL

    def _get_capability(self) -> SourceCapability:
        """定义数据源能力"""
        return SourceCapability(
            supported_types={
                DataType.STOCK_REALTIME,
            },
            realtime=True,
            historical=False,
            batch_query=True,
            max_batch_size=5000,
            requires_token=False,
            rate_limit=0
        )

    def _check_config(self) -> bool:
        """检查配置（东方财富无需特殊配置）"""
        return True

    def fetch_limit_up_stocks(self, page: int = 1, page_size: int = 5000) -> List[Dict]:
        """
        获取涨停股票列表

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            涨停股票列表
        """
        try:
            # 构建请求参数
            # fs参数: m:0+t:6 沪深A股, m:0+t:80 沪深主板, m:1+t:2 科创板, m:1+t:23 北交所
            params = {
                'np': 1,
                'fltt': 2,
                'invt': 2,
                'fid': 'f3',  # 按涨幅排序
                'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',  # 全市场
                'fields': 'f8,f9,f12,f13,f14,f2,f3,f4,f5,f6,f7,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f27,f28,f29,f30,f31,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100,f101,f102,f103,f104,f105,f106,f107,f108,f109,f110,f111,f112,f113,f114,f115,f116,f117,f118,f119,f120,f121,f122,f123,f124,f125,f126',
                'fwt': '1',
                'pn': page,
                'pz': page_size,
                'po': '1',  # 1=升序(涨幅从小到大)，配合fid=f3过滤，实际返回涨幅榜前列；0=降序返回跌幅榜
                'erp': '1',
            }

            # 带重试的请求
            response = None
            for retry in range(self.MAX_RETRIES + 1):
                try:
                    response = self.session.get(self.base_url, params=params, timeout=15)
                    response.encoding = 'utf-8'

                    if response.status_code == 200:
                        break  # 成功，跳出重试循环
                    else:
                        if retry < self.MAX_RETRIES:
                            logger.warning(f"东方财富API HTTP {response.status_code}，重试 {retry + 1}/{self.MAX_RETRIES}")
                            time.sleep(2 ** retry)
                        else:
                            logger.error(f"东方财富API请求失败: {response.status_code}")
                            self.metrics.record_failure()
                            return []

                except requests.exceptions.Timeout:
                    if retry < self.MAX_RETRIES:
                        logger.warning(f"东方财富API请求超时，重试 {retry + 1}/{self.MAX_RETRIES}")
                        time.sleep(2 ** retry)
                    else:
                        logger.error("东方财富API请求超时")
                        self.metrics.record_failure()
                        return []
                except requests.exceptions.ConnectionError:
                    if retry < self.MAX_RETRIES:
                        logger.warning(f"东方财富API连接错误，重试 {retry + 1}/{self.MAX_RETRIES}")
                        time.sleep(2 ** retry)
                    else:
                        logger.error("东方财富API连接错误")
                        self.metrics.record_failure()
                        return []
                except Exception as e:
                    if retry < self.MAX_RETRIES:
                        logger.warning(f"东方财富API请求异常: {e}，重试 {retry + 1}/{self.MAX_RETRIES}")
                        time.sleep(2 ** retry)
                    else:
                        logger.error(f"东方财富API请求异常: {e}")
                        self.metrics.record_failure()
                        return []

            if response is None or response.status_code != 200:
                self.metrics.record_failure()
                return []

            data = response.json()

            if data.get('rc') != 0:
                logger.error(f"东方财富API返回错误: {data.get('rt')}")
                self.metrics.record_failure()
                return []

            # 数据在 data.data.diff 下
            data_obj = data.get('data', {})
            diff = data_obj.get('diff', [])
            if not diff:
                logger.info("未获取到股票数据")
                return []

            # 解析数据
            stocks = []
            for item in diff:
                try:
                    code = item.get('f12', '')
                    name = item.get('f14', '')
                    price = safe_float(item.get('f2'))
                    change_pct = safe_float(item.get('f3')) / 100  # 转换为小数
                    open_price = safe_float(item.get('f17'))
                    high = safe_float(item.get('f15'))
                    low = safe_float(item.get('f16'))
                    volume = safe_int(item.get('f5'))  # 手
                    amount = safe_float(item.get('f6'))  # 元
                    turnover = safe_float(item.get('f8'))  # 换手率

                    stocks.append({
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
                        'data_source': 'EastMoney'
                    })
                except Exception as e:
                    logger.debug(f"解析股票数据失败: {e}")
                    continue

            self.metrics.record_success(0.3)
            logger.info(f"东方财富数据源成功获取 {len(stocks)} 只股票")
            return stocks

        except Exception as e:
            self.metrics.record_failure()
            logger.error(f"东方财富数据源获取涨停股失败: {e}")
            return []

    def fetch_stock_spot(self, stock_codes: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取A股实时行情（用于兼容接口）

        注意：此数据源主要用于涨停股查询，不支持指定股票代码查询
        """
        # 获取全市场数据并返回DataFrame
        stocks = self.fetch_limit_up_stocks()

        if not stocks:
            return pd.DataFrame()

        df = pd.DataFrame(stocks)

        # 重命名列以匹配标准格式
        column_mapping = {
            'code': '代码',
            'name': '名称',
            'price': '最新价',
            'change_pct': '涨跌幅',
            'open': '今开',
            'high': '最高',
            'low': '最低',
            'volume': '成交量',
            'amount': '成交额',
            'turnover': '换手率',
        }
        df = df.rename(columns=column_mapping)

        return df


# 测试代码
