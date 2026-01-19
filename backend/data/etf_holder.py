"""
ETF持仓数据获取模块
从东方财富等数据源获取ETF的持仓权重信息
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
from typing import List, Dict
from loguru import logger


class ETFHolderFetcher:
    """ETF持仓数据获取器"""

    def __init__(self):
        self.base_url = "http://fund.eastmoney.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def get_etf_holdings(self, etf_code: str) -> pd.DataFrame:
        """
        获取ETF的持仓明细

        Args:
            etf_code: ETF代码，如 "510300"

        Returns:
            DataFrame with columns: [股票代码, 股票名称, 持仓权重, 持仓股数]
        """
        try:
            url = f"{self.base_url}/{etf_code}.html"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')

            # 查找持仓数据（通常在页面中有特定标签）
            holdings = self._parse_holdings_from_page(soup, etf_code)

            if not holdings.empty:
                logger.info(f"成功获取ETF {etf_code} 的持仓数据，共 {len(holdings)} 只股票")
            else:
                logger.warning(f"ETF {etf_code} 未获取到持仓数据")

            return holdings

        except Exception as e:
            logger.error(f"获取ETF {etf_code} 持仓数据失败: {e}")
            return pd.DataFrame()

    def _parse_holdings_from_page(self, soup: BeautifulSoup, etf_code: str) -> pd.DataFrame:
        """从HTML页面解析持仓数据"""

        # 方法1: 尝试从JS变量中获取（东方财富常见方式）
        script_tags = soup.find_all('script')
        for script in script_tags:
            script_text = script.string
            if script_text and 'Data_holdStockDetail' in script_text:
                try:
                    # 提取JSON数据
                    start = script_text.find('[')
                    end = script_text.rfind(']') + 1
                    json_str = script_text[start:end]
                    data = json.loads(json_str)

                    holdings_list = []
                    for item in data:
                        holdings_list.append({
                            '股票代码': item.get('code', ''),
                            '股票名称': item.get('name', ''),
                            '持仓权重': float(item.get('weight', 0)) / 100,  # 转换为小数
                            '持仓股数': int(item.get('amount', 0))
                        })

                    return pd.DataFrame(holdings_list)

                except Exception as e:
                    logger.debug(f"解析JS变量失败: {e}")
                    continue

        # 方法2: 从API接口获取
        return self._get_etf_holdings_from_api(etf_code)

    def _get_etf_holdings_from_api(self, etf_code: str) -> pd.DataFrame:
        """从API接口获取ETF持仓数据"""

        try:
            # 东方财富持仓API
            api_url = f"http://fund.eastmoney.com/pingzhongdata/{etf_code}.js"
            response = requests.get(api_url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                content = response.text
                # 解析var Data_holdStockDetail = [...]
                if 'Data_holdStockDetail' in content:
                    start = content.find('[')
                    end = content.rfind(']') + 1
                    json_str = content[start:end]
                    data = json.loads(json_str)

                    holdings_list = []
                    for item in data:
                        holdings_list.append({
                            '股票代码': item.get('code', ''),
                            '股票名称': item.get('name', ''),
                            '持仓权重': float(item.get('weight', 0)) / 100,
                            '持仓股数': int(item.get('amount', 0))
                        })

                    return pd.DataFrame(holdings_list)

        except Exception as e:
            logger.debug(f"API获取失败: {e}")

        return pd.DataFrame()

    def build_stock_etf_mapping(self, stock_codes: List[str],
                                 etf_codes: List[str]) -> Dict[str, List[Dict]]:
        """
        构建股票代码到ETF的映射关系

        Args:
            stock_codes: 股票代码列表
            etf_codes: ETF代码列表

        Returns:
            {
                "股票代码": [
                    {"etf_code": "510300", "etf_name": "沪深300ETF", "weight": 0.08},
                    ...
                ]
            }
        """
        mapping = {}

        logger.info(f"开始构建映射关系，{len(etf_codes)} 个ETF")

        for etf_code in etf_codes:
            holdings = self.get_etf_holdings(etf_code)

            if holdings.empty:
                continue

            for _, row in holdings.iterrows():
                stock_code = row['股票代码']

                # 只关注我们关注的股票
                if stock_codes and stock_code not in stock_codes:
                    continue

                weight = row['持仓权重']

                # 过滤掉权重太小的
                if weight < 0.01:  # 小于1%的忽略
                    continue

                if stock_code not in mapping:
                    mapping[stock_code] = []

                mapping[stock_code].append({
                    'etf_code': etf_code,
                    'etf_name': self._get_etf_name(etf_code),
                    'weight': weight
                })

            time.sleep(0.5)  # 避免请求过快

        # 按权重排序
        for stock_code in mapping:
            mapping[stock_code].sort(key=lambda x: x['weight'], reverse=True)

        logger.info(f"映射关系构建完成，覆盖 {len(mapping)} 只股票")

        return mapping

    def _get_etf_name(self, etf_code: str) -> str:
        """获取ETF名称"""
        # 可以从缓存或配置中获取
        etf_names = {
            "510300": "沪深300ETF",
            "510500": "中证500ETF",
            "159915": "创业板ETF",
            "588000": "科创50ETF",
            "512480": "计算机ETF",
            "159995": "芯片ETF",
            "516160": "新能源车ETF"
        }
        return etf_names.get(etf_code, f"ETF{etf_code}")

    def save_mapping(self, mapping: Dict, filepath: str = "data/stock_etf_mapping.json"):
        """保存映射关系到文件"""
        import json

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        logger.info(f"映射关系已保存到 {filepath}")

    def load_mapping(self, filepath: str = "data/stock_etf_mapping.json") -> Dict:
        """从文件加载映射关系"""
        import json
        import os

        if not os.path.exists(filepath):
            logger.warning(f"映射文件不存在: {filepath}")
            return {}

        with open(filepath, 'r', encoding='utf-8') as f:
            mapping = json.load(f)

        logger.info(f"从 {filepath} 加载了 {len(mapping)} 只股票的映射关系")

        return mapping


# 测试代码
if __name__ == "__main__":
    fetcher = ETFHolderFetcher()

    # 测试获取单个ETF持仓
    holdings = fetcher.get_etf_holdings("510300")
    if not holdings.empty:
        print("\n沪深300ETF前十大持仓:")
        print(holdings.head(10).to_string(index=False))
