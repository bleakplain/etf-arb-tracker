"""
Mock utilities for testing

Provides ready-to-use mock implementations for common interfaces.
"""

from typing import Dict, List, Optional
from unittest.mock import Mock
from datetime import datetime

from backend.market.interfaces import IQuoteFetcher, IETFHoldingProvider
from backend.signal.interfaces import ISignalEvaluator
from backend.market.events import MarketEvent
from backend.market import CandidateETF


class MockQuoteFetcher(IQuoteFetcher):
    """Mock行情获取器"""

    def __init__(self, quotes: Dict[str, Dict] = None):
        """
        初始化Mock行情获取器

        Args:
            quotes: 预设的行情数据 {code: quote_dict}
        """
        self._quotes = quotes or self._get_default_quotes()

    def _get_default_quotes(self) -> Dict[str, Dict]:
        """获取默认行情数据"""
        return {
            '600519': {
                'code': '600519',
                'name': '贵州茅台',
                'price': 1800.0,
                'change_pct': 0.1001,  # 涨停
                'is_limit_up': True,
                'timestamp': '14:00:00',
                'volume': 1000000,
                'amount': 1800000000
            },
            '300750': {
                'code': '300750',
                'name': '宁德时代',
                'price': 256.80,
                'change_pct': 0.2001,  # 涨停
                'is_limit_up': True,
                'timestamp': '13:30:00',
                'volume': 5000000,
                'amount': 1284000000
            },
            '000001': {
                'code': '000001',
                'name': '平安银行',
                'price': 12.50,
                'change_pct': 0.015,  # 未涨停
                'is_limit_up': False,
                'timestamp': '14:30:00',
                'volume': 8000000,
                'amount': 100000000
            }
        }

    def get_stock_quote(self, code: str) -> Optional[Dict]:
        """获取股票行情"""
        return self._quotes.get(code)

    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取股票行情"""
        return {code: self._quotes.get(code) for code in codes}

    def is_trading_time(self) -> bool:
        """判断是否交易时间"""
        return True

    def set_quote(self, code: str, quote: Dict) -> None:
        """设置行情数据"""
        self._quotes[code] = quote


class MockETFHolderProvider(IETFHoldingProvider):
    """Mock ETF持仓关系提供者"""

    def __init__(self, mapping: Dict[str, List[Dict]] = None):
        """
        初始化Mock持仓关系提供者

        Args:
            mapping: 预设的股票-ETF映射
        """
        self._mapping = mapping or self._get_default_mapping()

    def _get_default_mapping(self) -> Dict[str, List[Dict]]:
        """获取默认映射数据"""
        return {
            '600519': [
                {'etf_code': '510300', 'etf_name': '沪深300ETF'},
                {'etf_code': '510500', 'etf_name': '中证500ETF'},
            ],
            '300750': [
                {'etf_code': '516160', 'etf_name': '新能源车ETF'},
            ]
        }

    def get_etf_top_holdings(self, etf_code: str) -> Optional[Dict]:
        """获取ETF前十大持仓"""
        holdings_map = {
            '510300': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.08},
                {'stock_code': '600036', 'stock_name': '招商银行', 'weight': 0.05},
            ],
            '510500': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.04},
            ],
            '516160': [
                {'stock_code': '300750', 'stock_name': '宁德时代', 'weight': 0.085},
            ]
        }

        holdings = holdings_map.get(etf_code, [])
        return {
            'etf_code': etf_code,
            'etf_name': f'ETF_{etf_code}',
            'top_holdings': holdings,
            'total_weight': sum(h['weight'] for h in holdings)
        }

    def load_mapping(self, filepath: str) -> Optional[Dict]:
        """加载映射关系"""
        return self._mapping

    def save_mapping(self, mapping: Dict, filepath: str) -> None:
        """保存映射关系"""
        self._mapping = mapping

    def build_stock_etf_mapping(self, stock_codes: List[str], etf_codes: List[str]) -> Dict:
        """构建映射关系"""
        return {code: self._mapping.get(code, []) for code in stock_codes}


class MockETFHoldingsProvider(IETFHoldingProvider):
    """Mock ETF持仓详情提供者"""

    def __init__(self, holdings: Dict[str, List[Dict]] = None):
        """
        初始化Mock持仓详情提供者

        Args:
            holdings: 预设的ETF持仓数据
        """
        self._holdings = holdings or self._get_default_holdings()

    def _get_default_holdings(self) -> Dict[str, List[Dict]]:
        """获取默认持仓数据"""
        return {
            '510300': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.08},
                {'stock_code': '600036', 'stock_name': '招商银行', 'weight': 0.05},
            ],
            '510500': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.04},
            ],
            '516160': [
                {'stock_code': '300750', 'stock_name': '宁德时代', 'weight': 0.085},
            ]
        }

    def get_etf_top_holdings(self, etf_code: str) -> Optional[Dict]:
        """获取ETF前十大持仓"""
        holdings = self._holdings.get(etf_code, [])
        return {
            'etf_code': etf_code,
            'etf_name': f'ETF_{etf_code}',
            'top_holdings': holdings,
            'total_weight': sum(h['weight'] for h in holdings)
        }

    def load_mapping(self, filepath: str) -> Optional[Dict]:
        """加载映射关系"""
        return None

    def save_mapping(self, mapping: Dict, filepath: str) -> None:
        """保存映射关系"""
        pass

    def build_stock_etf_mapping(self, stock_codes: List[str], etf_codes: List[str]) -> Dict:
        """构建映射关系"""
        return {}


class MockETFQuoteProvider(IQuoteFetcher):
    """Mock ETF行情提供者"""

    def __init__(self, quotes: Dict[str, Dict] = None):
        """
        初始化Mock ETF行情提供者

        Args:
            quotes: 预设的ETF行情数据
        """
        self._quotes = quotes or self._get_default_quotes()

    def _get_default_quotes(self) -> Dict[str, Dict]:
        """获取默认ETF行情数据"""
        return {
            '510300': {
                'code': '510300',
                'name': '沪深300ETF',
                'price': 4.567,
                'change_pct': 1.2,
                'premium': 0.5,
                'volume': 100000000,
                'amount': 456700000
            },
            '510500': {
                'code': '510500',
                'name': '中证500ETF',
                'price': 7.123,
                'change_pct': 0.8,
                'premium': -0.3,
                'volume': 80000000,
                'amount': 569840000
            },
            '516160': {
                'code': '516160',
                'name': '新能源车ETF',
                'price': 1.234,
                'change_pct': 2.5,
                'premium': 1.2,
                'volume': 50000000,
                'amount': 61700000
            }
        }

    def get_stock_quote(self, code: str) -> Optional[Dict]:
        """获取ETF行情"""
        return self._quotes.get(code)

    def get_etf_quote(self, code: str) -> Optional[Dict]:
        """获取ETF行情（别名方法）"""
        return self._quotes.get(code)

    def get_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取ETF行情"""
        return {code: self._quotes.get(code) for code in codes}

    def get_etf_batch_quotes(self, codes: List[str]) -> Dict[str, Optional[Dict]]:
        """批量获取ETF行情（别名方法）"""
        return self.get_batch_quotes(codes)

    def is_trading_time(self) -> bool:
        """判断是否交易时间"""
        return True

    def check_liquidity(self, code: str, min_amount: int = 50000000) -> bool:
        """检查流动性"""
        quote = self._quotes.get(code)
        if quote:
            return quote.get('amount', 0) >= min_amount
        return False


class MockSignalEvaluator(ISignalEvaluator):
    """Mock信号评估器"""

    def __init__(self, confidence: str = "中", risk_level: str = "中"):
        """
        初始化Mock信号评估器

        Args:
            confidence: 默认置信度
            risk_level: 默认风险等级
        """
        self._confidence = confidence
        self._risk_level = risk_level
        self.evaluate_calls = []

    def evaluate(
        self,
        market_event: MarketEvent,
        etf_holding: CandidateETF
    ) -> tuple[str, str]:
        """评估信号质量"""
        self.evaluate_calls.append((market_event, etf_holding))
        return (self._confidence, self._risk_level)

    def set_evaluation(self, confidence: str, risk_level: str) -> None:
        """设置评估结果"""
        self._confidence = confidence
        self._risk_level = risk_level


class MockHTTPClient:
    """Mock HTTP客户端"""

    def __init__(self):
        """初始化Mock HTTP客户端"""
        from backend.market.interfaces import HTTPResponse
        self._responses: Dict[str, HTTPResponse] = {}
        self._default_response = HTTPResponse(status_code=404, text="")
        self.request_log = []

    def set_response(self, url: str, status_code: int, text: str) -> None:
        """设置URL的响应"""
        from backend.market.interfaces import HTTPResponse
        self._responses[url] = HTTPResponse(status_code=status_code, text=text)

    def set_default_response(self, status_code: int, text: str) -> None:
        """设置默认响应"""
        from backend.market.interfaces import HTTPResponse
        self._default_response = HTTPResponse(status_code=status_code, text=text)

    def get(self, url: str, headers: Dict[str, str] = None, timeout: int = 10):
        """返回预设的响应"""
        self.request_log.append({'url': url, 'headers': headers, 'timeout': timeout})
        return self._responses.get(url, self._default_response)

    def reset(self) -> None:
        """重置所有响应和日志"""
        self._responses.clear()
        self.request_log.clear()

    def get_request_log(self) -> List[Dict]:
        """获取请求日志"""
        return self.request_log.copy()


# ==============================================================================
# 便捷函数
# ==============================================================================

def create_mock_limit_up_event(code: str, name: str = None) -> MarketEvent:
    """创建Mock涨停事件"""
    from backend.market.cn.events import LimitUpEvent

    return LimitUpEvent(
        stock_code=code,
        stock_name=name or f'Stock_{code}',
        price=100.0,
        change_pct=0.1001,
        limit_time=datetime.now().strftime('%H:%M:%S'),
        timestamp=datetime.now().strftime('%H:%M:%S')
    )


def create_candidate_etf(
    etf_code: str,
    weight: float = 0.08,
    rank: int = 1,
    top10_ratio: float = 0.50
) -> CandidateETF:
    """创建Mock候选ETF"""
    from backend.market.models import ETFCategory

    return CandidateETF(
        etf_code=etf_code,
        etf_name=f'ETF_{etf_code}',
        weight=weight,
        category=ETFCategory.BROAD_INDEX,
        rank=rank,
        in_top10=rank <= 10,
        top10_ratio=top10_ratio
    )
