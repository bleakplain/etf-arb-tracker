"""
涨停股数据获取模块
自动获取当日所有涨停股票
使用新浪财经涨停板数据接口
"""

import requests
import json
from typing import List, Dict
from datetime import datetime, time
from loguru import logger


class LimitUpStocksFetcher:
    """涨停股票数据获取器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn'
        }

    def get_today_limit_ups(self) -> List[Dict]:
        """
        获取今日所有涨停股票

        使用新浪财经涨停板数据接口
        URL: http://hq.sinajs.cn/list=s_sh000001,s_sz399001 (获取大盘)
        URL: http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData

        Returns:
            [
                {
                    'code': '股票代码',
                    'name': '股票名称',
                    'price': 涨停价格,
                    'change_pct': 涨跌幅,
                    'limit_time': 封板时间,
                    'seal_amount': 封单金额(元),
                    'turnover': 换手率,
                    'volume': 成交量(手),
                    'amount': 成交额(元)
                },
                ...
            ]
        """
        try:
            # 方案1: 使用新浪财经涨停板数据API
            # 这个API专门返回涨停板股票
            url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"

            # 涨停板数据参数
            params = {
                'page': '1',
                'num': '500',
                'sort': 'symbol',
                'asc': '0',
                'node': 'hs_a',  # 沪深A股
                '_s_r_a': 'page',
                'page_num': '1',
                'scalar': '0.95',  # 涨幅阈值 9.5%以上
                'filters': '[(\" market\",\"!\",\"3\"),(\" market\",\"!\",\"4\"),(\" zt\",\">=\",\"0\")]',
                # zt字段: 1=涨停, 0=非涨停
            }

            # 获取所有A股行情，然后筛选涨停股
            all_stocks = self._get_all_stocks_from_sina()

            if not all_stocks:
                logger.warning("新浪财经数据获取失败，尝试备用方案")
                return self._get_limit_ups_from_eastmoney()

            # 筛选涨停股
            limit_up_stocks = []
            for stock in all_stocks:
                if self._is_limit_up(stock['code'], stock['change_pct']):
                    limit_up_stocks.append(stock)

            logger.info(f"从 {len(all_stocks)} 只股票中筛选出 {len(limit_up_stocks)} 只涨停股")
            return limit_up_stocks

        except Exception as e:
            logger.error(f"获取涨停股异常: {e}")
            return self._get_limit_ups_from_eastmoney()

    def _get_all_stocks_from_sina(self) -> List[Dict]:
        """从新浪财经获取所有A股行情"""
        stocks = []

        try:
            # 使用新浪财经批量接口获取所有A股
            # 沪市600xxx, 601xxx, 603xxx, 688xxx
            # 深市000xxx, 002xxx, 003xxx, 300xxx

            # 获取涨幅榜前300名（涨停股肯定在里面）
            url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"

            for market_type in ['sh_a', 'sz_a']:
                params = {
                    'page': '1',
                    'num': '300',
                    'sort': 'changepercent',
                    'asc': '0',
                    'node': market_type
                }

                try:
                    response = requests.get(url, params=params, headers=self.headers, timeout=10)
                    response.encoding = 'gbk'

                    # 新浪返回的是JSONP格式，需要解析
                    text = response.text.strip()
                    if text.startswith('var hq_str_'):
                        # 这是实时行情格式
                        continue

                    # 尝试解析JSON
                    if text.startswith('/*'):
                        # 去掉JSONP包装
                        text = text[text.index('(')+1:text.rindex(')')]

                    data = json.loads(text) if text else []

                    for item in data:
                        change_pct = float(item.get('changepercent', 0))

                        stocks.append({
                            'code': item.get('symbol', ''),
                            'name': item.get('name', ''),
                            'price': float(item.get('trade', 0)),
                            'change_pct': change_pct,
                            'open': float(item.get('open', 0)),
                            'high': float(item.get('high', 0)),
                            'low': float(item.get('low', 0)),
                            'volume': int(float(item.get('volume', 0))),  # 股
                            'amount': float(item.get('amount', 0)),  # 元
                            'turnover': 0,
                            'limit_time': '',
                            'seal_amount': 0
                        })

                except Exception as e:
                    logger.debug(f"获取{market_type}数据失败: {e}")
                    continue

            return stocks

        except Exception as e:
            logger.error(f"从新浪获取股票数据失败: {e}")
            return []

    def _get_limit_ups_from_eastmoney(self) -> List[Dict]:
        """备用方案：从东方财富获取涨停股"""
        try:
            # 使用东方财富涨停板页面API
            url = "http://push2.eastmoney.com/api/qt/clist/get"

            # 涨停板数据参数
            params = {
                'pn': '1',
                'pz': '200',
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',  # 按涨跌幅排序
                'fs': 'b:MK0021,b:MK0022,b:MK0023,b:MK0024',  # 沪深A股所有板块
                # MK0021=沪主板, MK0022=深主板, MK0023=创业板, MK0024=科创板
                'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f22,f33,f11,f62,f128,f136,f115,f152'
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=15)
            data = response.json()

            if data.get('rc') != 0:
                logger.error(f"东方财富API返回错误: {data}")
                return []

            stocks = []
            diff = data.get('data', {}).get('diff', [])

            for item in diff:
                # f3 = 涨跌幅(万分之)，需要除以100
                change_pct = item.get('f3', 0) / 100
                code = item.get('f12', '')

                # 严格判断涨停
                if not self._is_limit_up(code, change_pct):
                    continue

                stocks.append({
                    'code': code,  # 纯数字代码，不带前缀
                    'name': item.get('f14', ''),
                    'price': item.get('f2', 0) / 1000,  # f2价格(毫)
                    'change_pct': change_pct,
                    'open': item.get('f17', 0) / 1000,
                    'high': item.get('f15', 0) / 1000,
                    'low': item.get('f16', 0) / 1000,
                    'volume': item.get('f5', 0),  # 成交量(手)
                    'amount': item.get('f6', 0),   # 成交额(元)
                    'turnover': item.get('f8', 0) / 100 if item.get('f8') else 0,  # 换手率(百)
                    'limit_time': '',
                    'seal_amount': 0
                })

            logger.info(f"从东方财富获取到 {len(stocks)} 只涨停股")
            return stocks

        except Exception as e:
            logger.error(f"从东方财富获取涨停股失败: {e}")
            return []

    def _is_limit_up(self, code: str, change_pct: float) -> bool:
        """
        判断是否涨停（严格判断）

        Args:
            code: 股票代码
            change_pct: 涨跌幅（小数形式，如0.0995表示9.95%）

        Returns:
            是否涨停
        """
        if change_pct < 0.095:  # 涨幅小于9.5%，肯定不是涨停
            return False

        # 根据板块判断涨停限制
        if code.startswith('688') or code.startswith('300'):
            # 科创板/创业板: 20%涨停
            # 允许一点误差（四舍五入）
            return change_pct >= 0.195
        elif code.startswith('8') or code.startswith('4'):
            # 北交所: 30%涨停
            return change_pct >= 0.295
        elif code.startswith('30'):
            # 创业板: 20%涨停
            return change_pct >= 0.195
        elif code.startswith('6') or code.startswith('00') or code.startswith('60'):
            # 主板: 10%涨停
            # ST股票是5%，但这里简化处理
            return change_pct >= 0.095
        else:
            # 其他情况，按10%计算
            return change_pct >= 0.095

    def get_hot_concepts(self) -> List[Dict]:
        """
        获取当日热门概念板块

        Returns:
            [
                {'name': '概念名称', 'code': '概念代码', 'change_pct': 涨幅},
                ...
            ]
        """
        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': '1',
                'pz': '50',
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': 'm:90+t:2',  # 概念板块
                'fields': 'f12,f14,f2,f3,f62'
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = response.json()

            concepts = []
            for item in data.get('data', {}).get('diff', []):
                concepts.append({
                    'code': item.get('f12', ''),
                    'name': item.get('f14', ''),
                    'change_pct': item.get('f3', 0) / 100,
                    'lead_stock': item.get('f62', '')  # 龙头股票
                })

            return concepts

        except Exception as e:
            logger.error(f"获取热门概念失败: {e}")
            return []


# 测试代码
if __name__ == "__main__":
    fetcher = LimitUpStocksFetcher()

    print("=" * 60)
    print("获取今日涨停股")
    print("=" * 60)

    limit_ups = fetcher.get_today_limit_ups()

    print(f"\n今日涨停股数量: {len(limit_ups)}")

    if limit_ups:
        print("\n前20只涨停股:")
        for i, stock in enumerate(limit_ups[:20], 1):
            print(f"{i}. {stock['name']} ({stock['code']}) - "
                  f"¥{stock['price']:.2f} (+{stock['change_pct']:.2f}%)")
    else:
        print("\n当前无涨停股或非交易时间")
