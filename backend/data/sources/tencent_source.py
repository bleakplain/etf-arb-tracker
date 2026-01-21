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
    is_limit_up,
    is_limit_down,
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

    def __init__(self, priority: int = 1):
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
            high = safe_float(fields[32]) if len(fields) > 32 else 0.0
            low = safe_float(fields[33]) if len(fields) > 33 else 0.0
            volume = safe_int(fields[35]) if len(fields) > 35 else 0
            amount = safe_float(fields[34]) if len(fields) > 34 else 0.0
            change = safe_float(fields[30]) if len(fields) > 30 else 0.0
            change_pct = safe_float(fields[31]) if len(fields) > 31 else 0.0

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

                try:
                    response = self.session.get(url, timeout=10)
                    response.encoding = 'gbk'

                    if response.status_code == 200:
                        for code in batch:
                            quote = self._parse_response(code, response.text)
                            if quote:
                                all_results[code] = quote

                    time.sleep(0.2)

                except Exception as e:
                    logger.warning(f"批量请求失败: {e}")

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
if __name__ == "__main__":
    fetcher = TencentDataSource()

    print("=" * 60)
    print("测试腾讯数据源")
    print("=" * 60)

    # 测试获取指定股票
    print("\n=== 测试获取指定股票 ===")
    codes = ["600519", "000001", "300750", "510300"]
    df = fetcher.fetch_by_codes(codes)

    if not df.empty:
        print(f"成功获取 {len(df)} 只股票:")
        print(df[['代码', '名称', '最新价', '涨跌幅']].to_string())
    else:
        print("获取失败")
