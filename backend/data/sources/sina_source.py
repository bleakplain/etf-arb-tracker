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
    DataSourceStatus,
    SourceCapability
)


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
        # 新浪API地址
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
            max_batch_size=200,  # 新浪支持更多
            requires_token=False,
            rate_limit=0
        )

    def _check_config(self) -> bool:
        """检查配置（新浪无需特殊配置）"""
        return True

    def _convert_to_sina_code(self, stock_code: str) -> str:
        """
        转换股票代码为新浪API格式

        Examples:
            600519 -> sh600519
            000001 -> sz000001
            300750 -> sz300750
        """
        if stock_code.startswith('6'):
            return f'sh{stock_code}'
        elif stock_code.startswith(('0', '3')):
            return f'sz{stock_code}'
        elif stock_code.startswith('8') or stock_code.startswith('4'):
            return f'bj{stock_code}'
        else:
            return stock_code

    def _parse_sina_response(self, stock_code: str, response_text: str) -> Optional[Dict]:
        """
        解析新浪API响应

        新浪API返回格式：
        var hq_str_sh600519="贵州茅台,1370.99,1375.00,1370.00,...";
        """
        try:
            sina_code = self._convert_to_sina_code(stock_code)
            search_pattern = f'hq_str_{sina_code}="'

            start_idx = response_text.find(search_pattern)
            if start_idx == -1:
                return None

            data_start = start_idx + len(search_pattern)
            data_end = response_text.find('";', data_start)
            if data_end == -1:
                # 尝试其他结束标记
                data_end = response_text.find('"', data_start)
                if data_end == -1:
                    return None

            data_str = response_text[data_start:data_end]

            # 检查是否为空
            if not data_str or data_str.strip() == '':
                return None

            fields = data_str.split(',')

            if len(fields) < 10:
                return None

            # 新浪API字段解析
            # 0:名称, 1:当前价, 2:昨收, 3:今开, 4:成交量(手), 5:外盘
            # 6:内盘, 7:买一, 8:买一量, 9:买二, 10:买二量 ...
            # 20:时间, 21:涨跌, 22:涨跌幅%, 23:最高, 24:最低, 25:成交量(手), 26:成交额(元), 27:换手率%
            name = fields[0] if fields[0] else ''
            price = self._safe_float(fields[1]) if len(fields) > 1 else 0.0
            prev_close = self._safe_float(fields[2]) if len(fields) > 2 else 0.0
            open_price = self._safe_float(fields[3]) if len(fields) > 3 else 0.0
            volume = self._safe_int(fields[4]) if len(fields) > 4 else 0
            high = self._safe_float(fields[23]) if len(fields) > 23 else 0.0
            low = self._safe_float(fields[24]) if len(fields) > 24 else 0.0
            amount = self._safe_float(fields[26]) if len(fields) > 26 else 0.0
            change = self._safe_float(fields[21]) if len(fields) > 21 else 0.0
            change_pct = self._safe_float(fields[22]) if len(fields) > 22 else 0.0
            turnover = self._safe_float(fields[27]) if len(fields) > 27 else 0.0
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

    def _safe_float(self, value) -> float:
        """安全地转换为float"""
        try:
            if value is None or value == '' or value == '-':
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _safe_int(self, value) -> int:
        """安全地转换为int"""
        try:
            if value is None or value == '' or value == '-':
                return 0
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    def _is_limit_up(self, code: str, change_pct: float) -> bool:
        """判断是否涨停"""
        if change_pct < 9.5:
            return False

        if code.startswith('688') or code.startswith('300'):
            return change_pct >= 19.5
        elif code.startswith('8') or code.startswith('4'):
            return change_pct >= 29.5
        else:
            return change_pct >= 9.5

    def _is_limit_down(self, code: str, change_pct: float) -> bool:
        """判断是否跌停"""
        if change_pct > -9.5:
            return False

        if code.startswith('688') or code.startswith('300'):
            return change_pct <= -19.5
        elif code.startswith('8') or code.startswith('4'):
            return change_pct <= -29.5
        else:
            return change_pct <= -9.5

    def fetch_stock_spot(self, stock_codes: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取A股实时行情

        如果未指定stock_codes，尝试获取全市场数据
        """
        start_time = time.time()

        try:
            if stock_codes is None:
                # 尝试获取上证所有股票
                stock_codes = self._get_all_stock_codes()

            if not stock_codes:
                logger.warning("没有可获取的股票代码")
                self.metrics.record_failure()
                return pd.DataFrame()

            logger.debug(f"使用新浪API获取 {len(stock_codes)} 只股票行情...")

            # 分批查询
            batch_size = 150  # 新浪支持更多
            all_results = {}

            for i in range(0, len(stock_codes), batch_size):
                batch = stock_codes[i:i + batch_size]
                sina_codes = [self._convert_to_sina_code(code) for code in batch]
                url = f"{self.list_url}{','.join(sina_codes)}"

                try:
                    response = self.session.get(url, timeout=15)
                    response.encoding = 'gbk'

                    if response.status_code == 200:
                        for code in batch:
                            quote = self._parse_sina_response(code, response.text)
                            if quote and quote['name']:  # 确保有名称
                                all_results[code] = quote

                    # 控制频率
                    time.sleep(0.15)

                except Exception as e:
                    logger.warning(f"新浪批量请求失败: {e}")

            if not all_results:
                self.metrics.record_failure()
                return pd.DataFrame()

            # 转换为DataFrame
            df = pd.DataFrame(list(all_results.values()))
            df = df.rename(columns={
                'code': '代码',
                'name': '名称',
                'price': '最新价',
                'prev_close': '昨收',
                'open': '今开',
                'high': '最高',
                'low': '最低',
                'volume': '成交量',
                'amount': '成交额',
                'change': '涨跌额',
                'change_pct': '涨跌幅',
                'turnover': '换手率',
            })

            # 添加涨停/跌停标记
            if '涨跌幅' in df.columns:
                df['is_limit_up'] = df.apply(
                    lambda row: self._is_limit_up(row['代码'], row['涨跌幅']),
                    axis=1
                )
                df['is_limit_down'] = df.apply(
                    lambda row: self._is_limit_down(row['代码'], row['涨跌幅']),
                    axis=1
                )

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
        # ETF使用相同接口
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
            # 获取上证主板
            url = f"{self.sse_list_url}?num=3000&sort=symbol&asc=1&node=hs_a&_s_r_a=page"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                # 解析JSON获取股票代码
                try:
                    import json
                    data = json.loads(response.text)
                    codes = []
                    for item in data:
                        code = item.get('symbol', '')
                        if code and len(code) == 6:
                            codes.append(code)
                    logger.info(f"从新浪获取 {len(codes)} 只A股代码")
                    return codes[:2000]  # 限制数量
                except:
                    pass

        except Exception as e:
            logger.warning(f"从新浪获取股票列表失败: {e}")

        # 返回空列表，让调用方决定如何处理
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
