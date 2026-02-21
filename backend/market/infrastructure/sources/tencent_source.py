"""
腾讯财经数据源 - 免费高频
使用腾讯财经API获取A股实时行情
"""

import pandas as pd
import time
import requests
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime

from backend.data.source_base import (
    BaseDataSource,
    SourceType,
    DataType,
    SourceCapability
)
from backend.data.utils import (
    safe_float,
    safe_int,
    convert_code_format
)
from backend.data.column_mappings import TENCENT_COLUMN_MAPPING
from backend.data.parsers import add_limit_flags


class TencentDataSource(BaseDataSource):
    """
    腾讯财经数据源

    特点：
    - 完全免费，无需token
    - 支持实时行情查询
    - 支持批量查询（每次最多100只股票）
    - 不支持全市场数据，需要指定股票代码
    """

    # 默认请求间隔（秒）- 防止被封禁
    DEFAULT_REQUEST_INTERVAL = 5
    # 最大重试次数
    MAX_RETRIES = 2

    def __init__(self, priority: int = 1, request_interval: Optional[float] = None):
        super().__init__(
            name="tencent",
            source_type=SourceType.FREE_HIGH_FREQ,
            priority=priority
        )
        self.base_url = 'http://qt.gtimg.cn/q'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self._common_stock_codes: Optional[List[str]] = None
        # 请求间隔，防止被封禁
        self._request_interval = request_interval or self.DEFAULT_REQUEST_INTERVAL

    def _get_capability(self) -> SourceCapability:
        """定义数据源能力"""
        return SourceCapability(
            supported_types={
                DataType.STOCK_REALTIME,
                DataType.ETF_REALTIME,
                DataType.INDEX,
            },
            realtime=True,
            historical=False,
            batch_query=True,
            max_batch_size=100,
            requires_token=False,
            rate_limit=0
        )

    def _check_config(self) -> bool:
        """检查配置（腾讯无需特殊配置）"""
        return True

    def _parse_response(self, stock_code: str, response_text: str) -> Optional[Dict]:
        """
        解析腾讯API响应

        腾讯API返回格式：
        v_sh600519="1~贵州茅台~600519~1370.99~...~-2.56~-0.19~..."
        """
        try:
            tc_code = convert_code_format(stock_code, 'tencent')
            search_pattern = f'v_{tc_code}="'

            start_idx = response_text.find(search_pattern)
            if start_idx == -1:
                return None

            data_start = start_idx + len(search_pattern)
            data_end = response_text.find('";', data_start)
            if data_end == -1:
                return None

            data_str = response_text[data_start:data_end]
            fields = data_str.split('~')

            if len(fields) < 50:
                logger.debug(f"腾讯API返回数据字段不足: {len(fields)}")
                return None

            # 解析字段
            name = fields[1] if len(fields) > 1 else ''
            price = safe_float(fields[3]) if len(fields) > 3 else 0.0
            prev_close = safe_float(fields[4]) if len(fields) > 4 else 0.0
            open_price = safe_float(fields[5]) if len(fields) > 5 else 0.0
            high = safe_float(fields[33]) if len(fields) > 33 else 0.0
            low = safe_float(fields[34]) if len(fields) > 34 else 0.0
            # 字段35 格式: "价格/成交量/成交额"
            volume_str = fields[35] if len(fields) > 35 else ''
            if '/' in volume_str:
                parts = volume_str.split('/')
                volume = safe_int(parts[1]) if len(parts) > 1 else 0
                amount = safe_float(parts[2]) if len(parts) > 2 else 0.0
            else:
                volume = 0
                amount = 0.0
            # 字段31: 涨跌额, 字段32: 涨跌幅（百分数形式，需要除以100）
            change = safe_float(fields[31]) if len(fields) > 31 else 0.0
            change_pct = safe_float(fields[32]) if len(fields) > 32 else 0.0
            # 腾讯API返回的涨跌幅是百分数形式（如2.44表示2.44%），需要转换为小数形式（0.0244）
            change_pct = change_pct / 100 if change_pct != 0 else 0.0

            # 计算涨跌幅
            if prev_close > 0 and change_pct == 0:
                change = price - prev_close
                change_pct = (change / prev_close) if prev_close > 0 else 0

            timestamp = f"{fields[39]} {fields[19]}" if len(fields) > 39 else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return {
                'code': stock_code,
                'name': name,
                'price': price,
                'prev_close': prev_close,
                'open': open_price,
                'high': high,
                'low': low,
                'volume': volume,
                'amount': amount,
                'change': change,
                'change_pct': change_pct,
                'timestamp': timestamp,
                'data_source': 'Tencent'
            }

        except Exception as e:
            logger.error(f"解析腾讯API响应失败: {e}")
            return None

    def fetch_stock_spot(self, stock_codes: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取A股实时行情

        注意：腾讯API需要指定股票代码列表
        如果未提供stock_codes，返回空DataFrame
        """
        start_time = time.time()

        if stock_codes is None:
            if self._common_stock_codes:
                stock_codes = self._common_stock_codes
            else:
                logger.warning("腾讯API需要指定股票代码列表")
                self.metrics.record_failure()
                return pd.DataFrame()

        try:
            logger.debug(f"使用腾讯API获取 {len(stock_codes)} 只股票行情...")

            batch_size = 100
            all_results = {}

            for i in range(0, len(stock_codes), batch_size):
                batch = stock_codes[i:i + batch_size]
                tc_codes = [convert_code_format(code, 'tencent') for code in batch]
                url = f"{self.base_url}={','.join(tc_codes)}"

                # 带重试的请求
                for retry in range(self.MAX_RETRIES + 1):
                    try:
                        response = self.session.get(url, timeout=15)
                        response.encoding = 'gbk'

                        if response.status_code == 200:
                            for code in batch:
                                quote = self._parse_response(code, response.text)
                                if quote:
                                    all_results[code] = quote
                            break  # 成功，跳出重试循环
                        else:
                            if retry < self.MAX_RETRIES:
                                logger.warning(f"批量请求HTTP {response.status_code}，重试 {retry + 1}/{self.MAX_RETRIES}")
                                time.sleep(2 ** retry)  # 指数退避
                            else:
                                logger.error(f"批量请求失败，HTTP状态码: {response.status_code}")

                    except requests.exceptions.Timeout:
                        if retry < self.MAX_RETRIES:
                            logger.warning(f"批量请求超时，重试 {retry + 1}/{self.MAX_RETRIES}")
                            time.sleep(2 ** retry)
                        else:
                            logger.error(f"批量请求超时，批次 {i//batch_size + 1}")
                    except requests.exceptions.ConnectionError:
                        if retry < self.MAX_RETRIES:
                            logger.warning(f"批量请求连接错误，重试 {retry + 1}/{self.MAX_RETRIES}")
                            time.sleep(2 ** retry)
                        else:
                            logger.error(f"批量请求连接错误，批次 {i//batch_size + 1}")
                    except Exception as e:
                        if retry < self.MAX_RETRIES:
                            logger.warning(f"批量请求异常: {e}，重试 {retry + 1}/{self.MAX_RETRIES}")
                            time.sleep(2 ** retry)
                        else:
                            logger.error(f"批量请求失败: {e}")

                # 批次间请求间隔
                time.sleep(self._request_interval)

            if not all_results:
                self.metrics.record_failure()
                return pd.DataFrame()

            # 转换为DataFrame，使用统一的列名映射
            df = pd.DataFrame(list(all_results.values()))
            df = df.rename(columns=TENCENT_COLUMN_MAPPING)

            # 添加涨停/跌停标记
            df = add_limit_flags(df)

            elapsed = time.time() - start_time
            self.metrics.record_success(elapsed)
            logger.info(f"腾讯数据源成功获取 {len(df)} 只股票 (耗时: {elapsed:.2f}秒)")

            return df

        except Exception as e:
            elapsed = time.time() - start_time
            self.metrics.record_failure()
            logger.error(f"腾讯数据源获取A股行情失败: {e}")
            return pd.DataFrame()

    def fetch_etf_spot(self, etf_codes: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取ETF实时行情

        注意：腾讯API需要指定ETF代码列表
        """
        return self.fetch_stock_spot(etf_codes)

    def fetch_by_codes(self, codes: List[str]) -> pd.DataFrame:
        """
        批量获取指定代码的行情

        Args:
            codes: 股票/ETF代码列表

        Returns:
            行情DataFrame
        """
        return self.fetch_stock_spot(codes)

    def set_common_stocks(self, codes: List[str]):
        """设置常用股票代码列表（用于默认查询）"""
        self._common_stock_codes = codes
        logger.info(f"设置腾讯数据源常用股票列表: {len(codes)} 只")


# 测试代码
