"""
涨停监控策略引擎
实时监控自选股涨停情况，触发ETF买入信号

套利策略核心逻辑：
1. 个股涨停 → 无法买入
2. 查找该个股持仓占比>5%的ETF → 买入ETF替代
3. 通过ETF净值增长获得该个股涨停收益
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass, asdict

from backend.data.stock_quote import StockQuoteFetcher
from backend.data.etf_quote import ETFQuoteFetcher
from backend.data.etf_holder import ETFHolderFetcher
from backend.data.etf_holdings import ETFHoldingsFetcher


@dataclass
class TradingSignal:
    """交易信号数据类"""
    signal_id: str           # 信号ID
    timestamp: str           # 触发时间
    stock_code: str          # 涨停股票代码
    stock_name: str          # 涨停股票名称
    stock_price: float       # 涨停价格
    limit_time: str          # 涨停时间
    seal_amount: float       # 封单量（元）
    change_pct: float        # 涨跌幅

    etf_code: str            # 建议买入的ETF代码
    etf_name: str            # ETF名称
    etf_weight: float        # 该股票在ETF中的实际权重（从持仓数据获取）
    etf_price: float         # ETF当前价格
    etf_premium: float       # ETF溢价率

    reason: str              # 触发原因说明
    confidence: str          # 信号强度: 高/中/低
    risk_level: str          # 风险等级

    # 策略验证信息
    actual_weight: float     # 从ETF持仓数据获取的真实权重
    weight_rank: int         # 该股票在ETF中的排名
    top10_ratio: float       # 前十大持仓占比

    def to_dict(self):
        """转换为字典"""
        return asdict(self)


class LimitUpMonitor:
    """涨停监控器"""

    # 策略参数默认值
    DEFAULT_MIN_WEIGHT = 0.05      # 最小持仓权重 5%
    DEFAULT_MIN_SEAL_AMOUNT = 10   # 最小封单量 10亿
    DEFAULT_MIN_TIME_TO_CLOSE = 1800  # 距收盘最小时间 30分钟
    DEFAULT_MIN_ETF_VOLUME = 5000  # ETF最小日成交额 5000万

    def __init__(self, config_path: str = "config/settings.yaml"):
        """初始化监控器"""
        self.config = self._load_config(config_path)
        self.stock_fetcher = StockQuoteFetcher()
        self.etf_fetcher = ETFQuoteFetcher()
        self.holder_fetcher = ETFHolderFetcher()
        self.holdings_fetcher = ETFHoldingsFetcher()

        # 加载自选股
        self.watch_stocks = self._load_watch_stocks()
        # 加载ETF映射
        self.stock_etf_mapping = self._load_or_build_mapping()

        # 信号历史
        self.signal_history: List[TradingSignal] = []

        # 已处理的涨停股票（避免重复信号）
        self.processed_limits = set()

        logger.info("涨停监控器初始化完成")
        logger.info(f"监控股票数量: {len(self.watch_stocks)}")
        logger.info(f"覆盖ETF数量: {len(self.get_all_etfs())}")

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"配置文件加载成功: {config_path}")
            return config
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}，使用默认配置")
            # 返回默认配置
            return {
                'strategy': {
                    'min_weight': self.DEFAULT_MIN_WEIGHT,
                    'min_order_amount': self.DEFAULT_MIN_SEAL_AMOUNT,
                    'min_time_to_close': self.DEFAULT_MIN_TIME_TO_CLOSE,
                    'min_etf_volume': self.DEFAULT_MIN_ETF_VOLUME,
                }
            }

    def _load_watch_stocks(self) -> List[Dict]:
        """加载自选股列表"""
        try:
            with open("config/stocks.yaml", 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data.get('my_stocks', [])
        except Exception as e:
            logger.warning(f"加载自选股失败: {e}")
            return []

    def _load_or_build_mapping(self) -> Dict:
        """加载或构建股票-ETF映射"""
        # 先尝试加载已有映射
        mapping = self.holder_fetcher.load_mapping("data/stock_etf_mapping.json")

        if mapping:
            logger.info(f"加载已有映射，覆盖 {len(mapping)} 只股票")
            return mapping

        # 如果没有，构建新的映射
        logger.info("未找到已有映射，开始构建...")
        stock_codes = [s['code'] for s in self.watch_stocks]
        etf_codes = self._get_watch_etf_codes()

        mapping = self.holder_fetcher.build_stock_etf_mapping(stock_codes, etf_codes)
        self.holder_fetcher.save_mapping(mapping)

        return mapping

    def _get_watch_etf_codes(self) -> List[str]:
        """获取关注的ETF代码列表"""
        try:
            with open("config/stocks.yaml", 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return [e['code'] for e in data.get('watch_etfs', [])]
        except:
            # 默认ETF列表：主要宽基和行业ETF
            return [
                # 宽基
                "510300", "510500", "510050", "159915", "588000", "159901", "512100",
                # 科技
                "159995", "512480", "515000", "516160", "515790",
                # 消费
                "512590", "159928", "512170",
                # 金融
                "512880", "512800"
            ]

    def get_all_etfs(self) -> List[str]:
        """获取所有相关ETF代码"""
        etf_set = set()
        for etf_list in self.stock_etf_mapping.values():
            for etf in etf_list:
                etf_set.add(etf['etf_code'])
        return list(etf_set)

    @staticmethod
    def normalize_stock_code(stock_code: str) -> str:
        """
        标准化股票代码，去掉市场前缀

        Args:
            stock_code: 股票代码，可能带前缀如 sh688319, sz000001

        Returns:
            纯数字股票代码，如 688319, 000001
        """
        # 去掉市场前缀
        prefixes = ['sh', 'sz', 'bj']
        code = stock_code.lower()
        for prefix in prefixes:
            if code.startswith(prefix):
                return code[2:]
        return stock_code

    def find_related_etfs(self, stock_code: str) -> List[Dict]:
        """
        找到与股票相关的ETF（用于API展示）

        Returns:
            [{etf_code, etf_name, weight, category}, ...]
        """
        # 标准化股票代码
        normalized_code = self.normalize_stock_code(stock_code)

        # 先从映射中查找
        mapped_etfs = self.stock_etf_mapping.get(normalized_code, [])

        if mapped_etfs:
            return mapped_etfs

        # 如果没有映射，返回推荐ETF
        return self._get_recommended_etfs(normalized_code)

    def _get_recommended_etfs(self, stock_code: str) -> List[Dict]:
        """
        根据股票类型推荐通用ETF列表

        Args:
            stock_code: 股票代码（已标准化）

        Returns:
            推荐的ETF列表，包含多类ETF
        """
        # 根据股票代码前缀判断类型并推荐对应ETF
        if stock_code.startswith('688') or stock_code.startswith('300'):
            # 科创板/创业板
            return [
                {"etf_code": "588000", "etf_name": "科创50ETF", "weight": 0.05, "category": "宽基"},
                {"etf_code": "588200", "etf_name": "科创100ETF", "weight": 0.04, "category": "宽基"},
                {"etf_code": "159915", "etf_name": "创业板ETF", "weight": 0.05, "category": "宽基"},
                {"etf_code": "159995", "etf_name": "芯片ETF", "weight": 0.04, "category": "科技"},
                {"etf_code": "512480", "etf_name": "计算机ETF", "weight": 0.03, "category": "科技"},
                {"etf_code": "516160", "etf_name": "新能源车ETF", "weight": 0.03, "category": "科技"},
                {"etf_code": "510300", "etf_name": "沪深300ETF", "weight": 0.02, "category": "宽基"}
            ]
        elif stock_code.startswith('6') or stock_code.startswith('60'):
            # 沪市主板
            return [
                {"etf_code": "510300", "etf_name": "沪深300ETF", "weight": 0.04, "category": "宽基"},
                {"etf_code": "510050", "etf_name": "上证50ETF", "weight": 0.03, "category": "宽基"},
                {"etf_code": "510500", "etf_name": "中证500ETF", "weight": 0.03, "category": "宽基"},
                {"etf_code": "512800", "etf_name": "银行ETF", "weight": 0.02, "category": "金融"},
                {"etf_code": "512880", "etf_name": "证券ETF", "weight": 0.02, "category": "金融"},
                {"etf_code": "512590", "etf_name": "酒ETF", "weight": 0.02, "category": "消费"},
                {"etf_code": "159928", "etf_name": "消费ETF", "weight": 0.02, "category": "消费"}
            ]
        elif stock_code.startswith('00') or stock_code.startswith('001') or stock_code.startswith('002'):
            # 深市主板
            return [
                {"etf_code": "159915", "etf_name": "创业板ETF", "weight": 0.05, "category": "宽基"},
                {"etf_code": "510300", "etf_name": "沪深300ETF", "weight": 0.04, "category": "宽基"},
                {"etf_code": "159901", "etf_name": "深证100ETF", "weight": 0.03, "category": "宽基"},
                {"etf_code": "159995", "etf_name": "芯片ETF", "weight": 0.03, "category": "科技"},
                {"etf_code": "512590", "etf_name": "酒ETF", "weight": 0.02, "category": "消费"},
                {"etf_code": "159928", "etf_name": "消费ETF", "weight": 0.02, "category": "消费"},
                {"etf_code": "512170", "etf_name": "医药ETF", "weight": 0.02, "category": "消费"}
            ]
        elif stock_code.startswith('8') or stock_code.startswith('4'):
            # 北交所
            return [
                {"etf_code": "510300", "etf_name": "沪深300ETF", "weight": 0.02, "category": "宽基"},
                {"etf_code": "510500", "etf_name": "中证500ETF", "weight": 0.02, "category": "宽基"},
                {"etf_code": "512100", "etf_name": "中证1000ETF", "weight": 0.02, "category": "宽基"}
            ]
        else:
            # 默认返回全面ETF列表
            return [
                {"etf_code": "510300", "etf_name": "沪深300ETF", "weight": 0.04, "category": "宽基"},
                {"etf_code": "510500", "etf_name": "中证500ETF", "weight": 0.03, "category": "宽基"},
                {"etf_code": "510050", "etf_name": "上证50ETF", "weight": 0.03, "category": "宽基"},
                {"etf_code": "159915", "etf_name": "创业板ETF", "weight": 0.03, "category": "宽基"},
                {"etf_code": "588000", "etf_name": "科创50ETF", "weight": 0.03, "category": "宽基"},
                {"etf_code": "159995", "etf_name": "芯片ETF", "weight": 0.02, "category": "科技"},
                {"etf_code": "516160", "etf_name": "新能源车ETF", "weight": 0.02, "category": "科技"},
                {"etf_code": "512880", "etf_name": "证券ETF", "weight": 0.02, "category": "金融"},
                {"etf_code": "512590", "etf_name": "酒ETF", "weight": 0.02, "category": "消费"}
            ]

    def check_limit_up(self, stock_code: str) -> Optional[Dict]:
        """
        检查单只股票是否涨停

        Returns:
            涨停信息字典，如果未涨停返回None
        """
        quote = self.stock_fetcher.get_stock_quote(stock_code)

        if not quote:
            return None

        if not quote['is_limit_up']:
            return None

        # 检查是否已经处理过这个涨停
        limit_key = f"{stock_code}_{datetime.now().strftime('%Y%m%d')}"
        if limit_key in self.processed_limits:
            return None

        return {
            'code': quote['code'],
            'name': quote['name'],
            'price': quote['price'],
            'time': quote['timestamp'],
            'change_pct': quote['change_pct']
        }

    def get_stock_weight_in_etf(self, stock_code: str, etf_code: str) -> Dict:
        """
        获取股票在ETF中的实际权重和排名

        Returns:
            {
                'weight': 0.05,          # 实际权重
                'rank': 3,               # 在ETF中的排名
                'in_top10': True,        # 是否在前10
                'top10_ratio': 0.45      # 前10持仓总占比
            }
        """
        try:
            holdings_data = self.holdings_fetcher.get_etf_top_holdings(etf_code)

            if not holdings_data or not holdings_data.get('top_holdings'):
                return {'weight': 0, 'rank': -1, 'in_top10': False, 'top10_ratio': 0}

            holdings = holdings_data['top_holdings']

            # 查找股票在持仓中的位置
            rank = -1
            weight = 0
            for i, h in enumerate(holdings):
                if h['stock_code'] == stock_code:
                    rank = i + 1
                    weight = h['weight']
                    break

            return {
                'weight': weight,
                'rank': rank,
                'in_top10': rank > 0 and rank <= 10,
                'top10_ratio': holdings_data.get('total_weight', 0)
            }

        except Exception as e:
            logger.warning(f"获取 {stock_code} 在 {etf_code} 中的权重失败: {e}")
            return {'weight': 0, 'rank': -1, 'in_top10': False, 'top10_ratio': 0}

    def find_related_etfs_with_real_weight(self, stock_code: str) -> List[Dict]:
        """
        找到与股票相关的ETF，并获取真实持仓权重

        策略要求：股票在ETF中的持仓占比必须 ≥ 5%

        Returns:
            [{etf_code, etf_name, weight, rank, in_top10, top10_ratio}, ...]
            按实际权重降序排序
        """
        # 标准化股票代码
        normalized_code = self.normalize_stock_code(stock_code)

        # 先获取映射中的ETF
        mapped_etfs = self.stock_etf_mapping.get(normalized_code, [])

        # 获取ETF名称映射
        etf_names = {e['etf_code']: e['etf_name'] for e in mapped_etfs}

        # 确定要扫描的ETF列表
        if mapped_etfs:
            # 如果有预构建的映射，使用映射中的ETF
            etf_codes_to_scan = [e['etf_code'] for e in mapped_etfs]
        else:
            # 如果没有映射，扫描所有关注的ETF
            etf_codes_to_scan = self._get_watch_etf_codes()
            # 为这些ETF添加名称
            etf_names = self._get_etf_name_map(etf_codes_to_scan)

        results = []

        for etf_code in etf_codes_to_scan:
            # 获取真实持仓权重（使用标准化代码）
            weight_info = self.get_stock_weight_in_etf(normalized_code, etf_code)

            # 策略核心：只返回持仓占比 >= 5% 的ETF
            if weight_info['weight'] >= self.DEFAULT_MIN_WEIGHT:
                results.append({
                    'etf_code': etf_code,
                    'etf_name': etf_names.get(etf_code, f'ETF{etf_code}'),
                    'category': self._get_etf_category(etf_code),
                    'weight': weight_info['weight'],
                    'rank': weight_info['rank'],
                    'in_top10': weight_info['in_top10'],
                    'top10_ratio': weight_info['top10_ratio']
                })

        # 按实际权重降序排序
        results.sort(key=lambda x: x['weight'], reverse=True)

        if results:
            logger.info(f"{normalized_code} 符合策略的ETF: {len(results)}个")
            for r in results:
                logger.info(f"  - {r['etf_name']}: 权重{r['weight']*100:.2f}%, 排名第{r['rank']}")
        else:
            logger.debug(f"{normalized_code} 未找到持仓>=5%的ETF")

        return results

    def _get_etf_name_map(self, etf_codes: List[str]) -> Dict[str, str]:
        """获取ETF代码到名称的映射"""
        name_map = {
            "510300": "沪深300ETF", "510500": "中证500ETF", "510050": "上证50ETF",
            "159915": "创业板ETF", "588000": "科创50ETF", "159901": "深证100ETF",
            "512100": "中证1000ETF", "159995": "芯片ETF", "512480": "计算机ETF",
            "515000": "5GETF", "516160": "新能源车ETF", "515790": "光伏ETF",
            "512590": "酒ETF", "159928": "消费ETF", "512170": "医药ETF",
            "512880": "证券ETF", "512800": "银行ETF", "588200": "科创100ETF"
        }
        return {code: name_map.get(code, f'ETF{code}') for code in etf_codes}

    def _get_etf_category(self, etf_code: str) -> str:
        """根据ETF代码获取分类"""
        broad_based = ["510300", "510500", "510050", "159915", "588000", "159901", "512100", "588200"]
        tech = ["159995", "512480", "515000", "516160", "515790"]
        consumer = ["512590", "159928", "512170"]
        financial = ["512880", "512800"]

        if etf_code in broad_based:
            return "宽基"
        elif etf_code in tech:
            return "科技"
        elif etf_code in consumer:
            return "消费"
        elif etf_code in financial:
            return "金融"
        else:
            return "其他"

    def evaluate_signal_quality(self, limit_info: Dict,
                                 etf_info: Dict) -> Tuple[str, str]:
        """
        评估信号质量

        评估维度：
        1. 权重越高置信度越高
        2. 排名越前置信度越高
        3. 前10持仓占比越集中风险越高
        4. 时间因素（距收盘时间）

        Returns:
            (confidence, risk_level) - (置信度, 风险等级)
        """
        confidence = "中"
        risk_level = "中"

        # 1. 权重评估
        weight = etf_info.get('weight', 0)
        if weight >= 0.10:  # 10%以上
            confidence = "高"
        elif weight < 0.05:  # 5%以下
            confidence = "低"

        # 2. 排名评估
        rank = etf_info.get('rank', -1)
        if rank <= 3 and confidence != "高":
            confidence = "高"
        elif rank > 10:
            confidence = "低"

        # 3. 风险等级 - 时间因素
        time_to_close = self.stock_fetcher.get_time_to_close()
        if time_to_close < 600:  # 10分钟内
            risk_level = "高"
        elif time_to_close > 3600:  # 1小时以上
            risk_level = "低"

        # 4. 风险等级 - 持仓集中度
        top10_ratio = etf_info.get('top10_ratio', 0)
        if top10_ratio > 0.70:  # 前10占比超过70%，风险较高
            if risk_level == "低":
                risk_level = "中"
            elif risk_level == "中":
                risk_level = "高"

        # 5. 涨停时间因素
        # 早上涨停比尾盘涨停更可靠
        current_hour = datetime.now().hour
        if current_hour < 10:  # 10点前涨停
            if risk_level == "高":
                risk_level = "中"

        return confidence, risk_level

    def generate_signal(self, stock_code: str) -> Optional[TradingSignal]:
        """
        生成交易信号

        套利策略：
        1. 检查股票是否涨停
        2. 查找该股票持仓占比>=5%的ETF
        3. 选择权重最高的ETF
        4. 验证时间、流动性等条件
        5. 生成买入信号
        """
        # 1. 检查是否涨停
        limit_info = self.check_limit_up(stock_code)
        if not limit_info:
            return None

        # 2. 获取真实持仓权重的ETF列表
        related_etfs = self.find_related_etfs_with_real_weight(stock_code)
        if not related_etfs:
            logger.info(f"⚠️  {stock_code} {limit_info['name']} 涨停，但无持仓占比>=5%的ETF")
            return None

        # 3. 选择权重最高的ETF
        best_etf = related_etfs[0]
        logger.info(f"✓ 选择 {best_etf['etf_name']}，权重 {best_etf['weight']*100:.2f}%，排名第{best_etf['rank']}")

        # 4. 获取ETF行情
        etf_quote = self.etf_fetcher.get_etf_quote(best_etf['etf_code'])
        if not etf_quote:
            logger.warning(f"无法获取 {best_etf['etf_name']} 行情")
            return None

        # 5. 检查时间限制（避免尾盘风险）
        strategy = self.config.get('strategy', {})
        min_time = strategy.get('min_time_to_close', self.DEFAULT_MIN_TIME_TO_CLOSE)
        time_to_close = self.stock_fetcher.get_time_to_close()

        if time_to_close < min_time and time_to_close != -1:
            logger.info(f"⚠️  距收盘仅{time_to_close//60}分钟，时间不足，跳过")
            return None

        # 6. 检查ETF流动性
        min_volume = strategy.get('min_etf_volume', self.DEFAULT_MIN_ETF_VOLUME) * 10000
        if not self.etf_fetcher.check_liquidity(best_etf['etf_code'], min_volume):
            logger.info(f"⚠️  {best_etf['etf_name']} 流动性不足，跳过")
            return None

        # 7. 评估信号质量
        confidence, risk_level = self.evaluate_signal_quality(limit_info, best_etf)

        # 8. 生成信号
        signal = TradingSignal(
            signal_id=f"SIG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{stock_code}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            stock_code=stock_code,
            stock_name=limit_info['name'],
            stock_price=limit_info['price'],
            limit_time=limit_info['time'],
            seal_amount=0,  # TODO: 从Level-2获取封单量
            change_pct=limit_info['change_pct'],
            etf_code=best_etf['etf_code'],
            etf_name=best_etf['etf_name'],
            etf_weight=best_etf['weight'],
            etf_price=etf_quote['price'],
            etf_premium=etf_quote.get('premium', 0),
            reason=f"{limit_info['name']} 涨停 (+{limit_info['change_pct']:.2f}%)，在 {best_etf['etf_name']} 中持仓占比 {best_etf['weight']*100:.2f}% (排名第{best_etf['rank']})",
            confidence=confidence,
            risk_level=risk_level,
            actual_weight=best_etf['weight'],
            weight_rank=best_etf['rank'],
            top10_ratio=best_etf.get('top10_ratio', 0)
        )

        # 标记已处理
        limit_key = f"{stock_code}_{datetime.now().strftime('%Y%m%d')}"
        self.processed_limits.add(limit_key)

        logger.success(f"🎯 生成信号: {signal.stock_name} 涨停 -> 建议买入 {signal.etf_name}")
        logger.success(f"   权重: {signal.actual_weight*100:.2f}%, 排名: 第{signal.weight_rank}, 置信度: {signal.confidence}")

        return signal

    def scan_all_stocks(self) -> List[TradingSignal]:
        """
        扫描所有自选股，生成信号

        Returns:
            本次扫描生成的信号列表
        """
        signals = []

        logger.info(f"开始扫描 {len(self.watch_stocks)} 只自选股...")

        for stock in self.watch_stocks:
            try:
                signal = self.generate_signal(stock['code'])
                if signal:
                    signals.append(signal)
                    self.signal_history.append(signal)

                time.sleep(0.1)  # 避免请求过快

            except Exception as e:
                logger.error(f"扫描股票 {stock['code']} 失败: {e}")

        logger.info(f"扫描完成，生成 {len(signals)} 个信号")

        return signals

    def run_once(self) -> List[TradingSignal]:
        """执行一次监控扫描"""
        logger.info("=" * 50)
        logger.info(f"执行监控扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 检查是否交易时间
        if not self.stock_fetcher.is_trading_time():
            logger.info("当前不在交易时间")
            return []

        return self.scan_all_stocks()

    def run_loop(self, interval: int = 60):
        """
        持续运行监控

        Args:
            interval: 扫描间隔（秒）
        """
        logger.info(f"开始持续监控，扫描间隔: {interval}秒")

        try:
            while True:
                try:
                    signals = self.run_once()

                    # 发送通知
                    if signals:
                        self._send_notifications(signals)

                    # 等待下一次扫描
                    time.sleep(interval)

                except KeyboardInterrupt:
                    logger.info("收到停止信号，退出监控")
                    break
                except Exception as e:
                    logger.error(f"监控循环出错: {e}")
                    time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("监控已停止")

    def _send_notifications(self, signals: List[TradingSignal]):
        """发送信号通知"""
        from backend.notification.sender import create_sender_from_config

        sender = create_sender_from_config(self.config)

        for signal in signals:
            logger.info(f"📢 信号通知: {signal.stock_name} -> {signal.etf_name}")
            sender.send_signal(signal)

    def save_signals(self, filepath: str = "data/signals.json"):
        """保存信号历史到文件"""
        os.makedirs("data", exist_ok=True)

        signals_data = [s.to_dict() for s in self.signal_history]

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(signals_data, f, ensure_ascii=False, indent=2)

        logger.info(f"信号历史已保存，共 {len(self.signal_history)} 条")


def main():
    """主函数"""
    # 配置日志
    logger.add("logs/monitor_{time}.log", rotation="100 MB")

    # 创建监控器
    monitor = LimitUpMonitor()

    # 先执行一次扫描
    signals = monitor.run_once()

    if signals:
        for signal in signals:
            print("\n" + "=" * 60)
            print(f"📈 涨停ETF套利信号")
            print("=" * 60)
            print(f"时间: {signal.timestamp}")
            print(f"\n【涨停股票】")
            print(f"  代码: {signal.stock_code}")
            print(f"  名称: {signal.stock_name}")
            print(f"  价格: ¥{signal.stock_price:.2f}")
            print(f"  涨幅: +{signal.change_pct:.2f}%")
            print(f"\n【建议操作】")
            print(f"  买入ETF: {signal.etf_name} ({signal.etf_code})")
            print(f"  当前价格: ¥{signal.etf_price:.3f}")
            print(f"  持仓占比: {signal.actual_weight*100:.2f}% ✓ (≥5%)")
            print(f"  持仓排名: 第{signal.weight_rank}名")
            print(f"  前10占比: {signal.top10_ratio*100:.1f}%")
            print(f"  溢价率: {signal.etf_premium:+.2f}%")
            print(f"\n【信号评估】")
            print(f"  置信度: {signal.confidence}")
            print(f"  风险等级: {signal.risk_level}")
            print(f"  说明: {signal.reason}")
            print("=" * 60)

        # 保存信号
        monitor.save_signals()

    # 如果是交易时间，询问是否持续监控
    if monitor.stock_fetcher.is_trading_time():
        print("\n当前为交易时间，是否启动持续监控？(y/n): ", end="")
        # 在实际使用时可以用input()
        # choice = input().strip().lower()
        # if choice == 'y':
        #     monitor.run_loop(interval=60)
        print("演示模式，不启动持续监控")


if __name__ == "__main__":
    main()
