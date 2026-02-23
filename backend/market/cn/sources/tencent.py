"""
腾讯财经数据源 - 免费高频
使用腾讯财经API获取A股实时行情
"""

import requests
import time
from typing import Dict, List, Optional
from loguru import logger


class TencentSource:
    """
    腾讯财经数据源

    特点：
    - 完全免费，无需token
    - 支持实时行情查询
    - 支持批量查询（每次最多100只股票）
    """

    DEFAULT_REQUEST_INTERVAL = 5
    MAX_RETRIES = 2

    def __init__(self):
        self.base_url = 'http://qt.gtimg.cn/q'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _convert_code_format(self, code: str, target_format: str) -> str:
        """转换股票代码格式"""
        if target_format == 'tencent':
            if code.startswith('6'):
                return f'sh{code}'
            else:
                return f'sz{code}'
        return code

    def _parse_response(self, stock_code: str, response_text: str) -> Optional[Dict]:
        """解析腾讯API响应"""
        try:
            tc_code = self._convert_code_format(stock_code, 'tencent')
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
                return None

            def safe_float(val):
                try:
                    return float(val) if val else 0.0
                except (ValueError, TypeError):
                    return 0.0

            name = fields[1] if len(fields) > 1 else ''
            price = safe_float(fields[3]) if len(fields) > 3 else 0.0
            prev_close = safe_float(fields[4]) if len(fields) > 4 else 0.0
            change = safe_float(fields[31]) if len(fields) > 31 else 0.0
            change_pct = safe_float(fields[32]) if len(fields) > 32 else 0.0 / 100

            volume_str = fields[35] if len(fields) > 35 else ''
            if '/' in volume_str:
                parts = volume_str.split('/')
                volume = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                amount = safe_float(parts[2]) if len(parts) > 2 else 0.0
            else:
                volume = 0
                amount = 0.0

            # 判断是否涨停: 涨跌幅 >= 9.9% (考虑浮点误差)
            is_limit_up = change_pct >= 9.9

            return {
                'code': stock_code,
                'name': name,
                'price': price,
                'change_pct': change_pct,
                'volume': volume,
                'amount': amount,
                'is_limit_up': is_limit_up,
                'timestamp': '',
                'data_source': 'Tencent'
            }
        except Exception as e:
            logger.error(f"解析腾讯API响应失败: {e}")
            return None

    def get_quote(self, code: str) -> Optional[Dict]:
        """获取单个股票行情"""
        tc_code = self._convert_code_format(code, 'tencent')
        url = f"{self.base_url}={tc_code}"

        try:
            response = self.session.get(url, timeout=10)
            response.encoding = 'gbk'
            if response.status_code == 200:
                return self._parse_response(code, response.text)
        except Exception as e:
            logger.error(f"获取股票{code}行情失败: {e}")
        return None

    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取股票行情"""
        results = {}
        batch_size = 100

        for i in range(0, len(codes), batch_size):
            batch = codes[i:i + batch_size]
            tc_codes = [self._convert_code_format(code, 'tencent') for code in batch]
            url = f"{self.base_url}={','.join(tc_codes)}"

            try:
                response = self.session.get(url, timeout=15)
                response.encoding = 'gbk'
                if response.status_code == 200:
                    for code in batch:
                        quote = self._parse_response(code, response.text)
                        results[code] = quote
                time.sleep(self.DEFAULT_REQUEST_INTERVAL)
            except Exception as e:
                logger.error(f"批量获取行情失败: {e}")
                for code in batch:
                    results[code] = None

        return results

    def get_etf_quote(self, code: str) -> Optional[Dict]:
        """获取ETF行情"""
        return self.get_quote(code)

    def get_etf_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取ETF行情"""
        return self.get_batch_quotes(codes)

    def get_limit_ups(self) -> List[Dict]:
        """获取涨停股票（暂时返回空列表，需要其他数据源）"""
        return []

    def get_etf_top_holdings(self, etf_code: str) -> Optional[Dict]:
        """获取ETF前十大持仓（暂时返回空）"""
        return {'top_holdings': [], 'total_weight': 0}

    def build_stock_etf_mapping(self, stock_codes: List[str], etf_codes: List[str]) -> Dict:
        """构建证券-ETF映射关系（暂时返回空）"""
        return {}
