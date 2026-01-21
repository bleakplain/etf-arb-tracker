"""
新浪财经数据源 - 免费高频
使用新浪财经API获取A股实时行情
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
from backend.data.column_mappings import SINA_COLUMN_MAPPING
from backend.data.parsers import add_limit_flags


class SinaDataSource(BaseDataSource):
    """
    新浪财经数据源

    特点：
    - 完全免费，无需token
    - 支持实时行情查询
    - 支持批量查询
    - 支持沪深A股全市场列表获取
    """

    def __init__(self, priority: int = 2):
        super().__init__(
            name="sina",
            source_type=SourceType.FREE_HIGH_FREQ,
            priority=priority
        )
        self.list_url = 'http://hq.sinajs.cn/list='
        self.sse_list_url = 'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn'
        })

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
            max_batch_size=200,
            requires_token=False,
            rate_limit=0
        )

    def _check_config(self) -> bool:
        """检查配置（新浪无需特殊配置）"""
        return True

    def _parse_sina_response(self, stock_code: str, response_text: str) -> Optional[Dict]:
        """
        解析新浪API响应

        新浪API返回格式：
        var hq_str_sh600519="贵州茅台,1370.99,1375.00,1370.00,...";
        """
        try:
            sina_code = convert_code_format(stock_code, 'sina')
            search_pattern = f'hq_str_{sina_code}="'

            start_idx = response_text.find(search_pattern)
            if start_idx == -1:
                return None

            data_start = start_idx + len(search_pattern)
            data_end = response_text.find('";', data_start)
            if data_end == -1:
                data_end = response_text.find('"', data_start)
                if data_end == -1:
                    return None

            data_str = response_text[data_start:data_end]

            if not data_str or data_str.strip() == '':
                return None

            fields = data_str.split(',')

            if len(fields) < 10:
                return None

            # 新浪API字段解析: 0:名称, 1:当前价, 2:昨收, 3:今开, 4:成交量(手), 20:时间,
            # 21:涨跌, 22:涨跌幅%, 23:最高, 24:最低, 26:成交额(元), 27:换手率%
            name = fields[0] if fields[0] else ''
            price = safe_float(fields[1]) if len(fields) > 1 else 0.0
            prev_close = safe_float(fields[2]) if len(fields) > 2 else 0.0
            open_price = safe_float(fields[3]) if len(fields) > 3 else 0.0
            volume = safe_int(fields[4]) if len(fields) > 4 else 0
            high = safe_float(fields[23]) if len(fields) > 23 else 0.0
            low = safe_float(fields[24]) if len(fields) > 24 else 0.0
            amount = safe_float(fields[26]) if len(fields) > 26 else 0.0
            change = safe_float(fields[21]) if len(fields) > 21 else 0.0
            change_pct = safe_float(fields[22]) if len(fields) > 22 else 0.0
            turnover = safe_float(fields[27]) if len(fields) > 27 else 0.0
            timestamp = fields[20] if len(fields) > 20 else datetime.now().strftime("%H:%M:%S")

            # 计算涨跌幅
            if prev_close > 0 and change_pct == 0:
                change = price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close > 0 else 0

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
                'turnover': turnover,
                'timestamp': timestamp,
                'data_source': 'Sina'
            }

        except Exception as e:
            logger.debug(f"解析新浪API响应失败: {e}")
            return None

    def fetch_stock_spot(self, stock_codes: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取A股实时行情

        如果未指定stock_codes，尝试获取全市场数据
        """
        start_time = time.time()

        try:
            if stock_codes is None:
                stock_codes = self._get_all_stock_codes()

            if not stock_codes:
                logger.warning("没有可获取的股票代码")
                self.metrics.record_failure()
                return pd.DataFrame()

            logger.debug(f"使用新浪API获取 {len(stock_codes)} 只股票行情...")

            batch_size = 150
            all_results = {}

            for i in range(0, len(stock_codes), batch_size):
                batch = stock_codes[i:i + batch_size]
                sina_codes = [convert_code_format(code, 'sina') for code in batch]
                url = f"{self.list_url}{','.join(sina_codes)}"

                try:
                    response = self.session.get(url, timeout=15)
                    response.encoding = 'gbk'

                    if response.status_code == 200:
                        for code in batch:
                            quote = self._parse_sina_response(code, response.text)
                            if quote and quote['name']:
                                all_results[code] = quote

                    time.sleep(0.15)

                except Exception as e:
                    logger.warning(f"新浪批量请求失败: {e}")

            if not all_results:
                self.metrics.record_failure()
                return pd.DataFrame()

            # 转换为DataFrame，使用统一的列名映射
            df = pd.DataFrame(list(all_results.values()))
            df = df.rename(columns=SINA_COLUMN_MAPPING)

            # 添加涨停/跌停标记
            df = add_limit_flags(df)

            elapsed = time.time() - start_time
            self.metrics.record_success(elapsed)
            logger.info(f"新浪数据源成功获取 {len(df)} 只股票 (耗时: {elapsed:.2f}秒)")

            return df

        except Exception as e:
            elapsed = time.time() - start_time
            self.metrics.record_failure()
            logger.error(f"新浪数据源获取A股行情失败: {e}")
            return pd.DataFrame()

    def fetch_etf_spot(self, etf_codes: Optional[List[str]] = None) -> pd.DataFrame:
        """获取ETF实时行情"""
        return self.fetch_stock_spot(etf_codes)

    def fetch_by_codes(self, codes: List[str]) -> pd.DataFrame:
        """批量获取指定代码的行情"""
        return self.fetch_stock_spot(codes)

    def _get_all_stock_codes(self) -> List[str]:
        """
        获取所有A股代码列表
        从新浪获取股票列表
        """
        try:
            url = f"{self.sse_list_url}?num=3000&sort=symbol&asc=1&node=hs_a&_s_r_a=page"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                import json
                data = json.loads(response.text)
                codes = [item.get('symbol', '') for item in data if item.get('symbol') and len(item.get('symbol', '')) == 6]
                logger.info(f"从新浪获取 {len(codes)} 只A股代码")
                return codes[:2000]

        except Exception as e:
            logger.warning(f"从新浪获取股票列表失败: {e}")

        return []


# 测试代码
if __name__ == "__main__":
    fetcher = SinaDataSource()

    print("=" * 60)
    print("测试新浪数据源")
    print("=" * 60)

    # 测试获取指定股票
    print("\n=== 测试获取指定股票 ===")
    codes = ["600519", "000001", "300750", "510300", "159915"]
    df = fetcher.fetch_by_codes(codes)

    if not df.empty:
        print(f"成功获取 {len(df)} 只股票:")
        print(df[['代码', '名称', '最新价', '涨跌幅']].to_string())
    else:
        print("获取失败")
