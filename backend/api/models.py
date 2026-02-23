"""
API请求和响应模型

定义所有API的请求和响应数据结构
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict
from datetime import datetime


class StockQuoteResponse(BaseModel):
    """股票行情响应模型"""
    code: str
    name: str
    price: float
    change_pct: float
    is_limit_up: bool


class ETFQuoteResponse(BaseModel):
    """ETF行情响应模型"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: float
    premium: Optional[float] = None


class SignalResponse(BaseModel):
    """信号响应"""
    signal_id: str
    timestamp: str
    stock_code: str
    stock_name: str
    stock_price: float
    etf_code: str
    etf_name: str
    etf_price: float
    etf_weight: float
    confidence: str
    risk_level: str
    reason: str


class MonitorStatus(BaseModel):
    """监控状态"""
    is_running: bool
    is_trading_time: bool
    watch_stocks_count: int
    covered_etfs_count: int
    today_signals_count: int
    last_scan_time: Optional[str] = None


class LimitUpStockResponse(BaseModel):
    """涨停股票响应模型"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: int
    amount: float
    turnover: float
    limit_time: str
    locked_amount: int


class BacktestRequest(BaseModel):
    """回测请求"""
    start_date: str          # "20240101"
    end_date: str            # "20241231"
    granularity: str = "daily"  # daily, 5m, 15m, 30m
    min_weight: Optional[float] = None
    evaluator_type: str = "default"
    interpolation: str = "linear"
    max_stocks: Optional[int] = 0  # 0表示不限制，用于快速测试
    max_etfs: Optional[int] = 0    # 0表示不限制

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v):
        """验证日期格式"""
        if not v:
            raise ValueError('日期不能为空')
        try:
            dt = datetime.strptime(v, "%Y%m%d")
        except ValueError:
            raise ValueError('日期格式错误，应为YYYYMMDD格式，例如: 20240101')

        # 限制日期范围（防止极端值）
        min_date = datetime(2000, 1, 1)
        max_date = datetime(2099, 12, 31)

        if dt < min_date:
            raise ValueError('日期不能早于20000101')
        if dt > max_date:
            raise ValueError('日期不能晚于20991231')

        return v

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """验证结束日期必须晚于开始日期"""
        if 'start_date' in info.data:
            start_date = info.data['start_date']
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(v, "%Y%m%d")

            if end_dt < start_dt:
                raise ValueError('结束日期不能早于开始日期')

            # 限制回测时间跨度（最大10年）
            max_span_days = 365 * 10
            actual_span = (end_dt - start_dt).days
            if actual_span > max_span_days:
                raise ValueError(f'回测时间跨度不能超过10年（当前为{actual_span // 365}年）')

        return v

    @field_validator('granularity')
    @classmethod
    def validate_granularity(cls, v):
        """验证时间粒度"""
        valid_granularities = ["daily", "5m", "15m", "30m"]
        if v not in valid_granularities:
            raise ValueError(f'时间粒度必须是{valid_granularities}之一')
        return v

    @field_validator('min_weight')
    @classmethod
    def validate_min_weight(cls, v):
        """验证最小权重"""
        if v is not None:
            if not (0.001 <= v <= 1.0):
                raise ValueError('权重必须在0.001到1.0之间')
        return v

    @field_validator('evaluator_type')
    @classmethod
    def validate_evaluator_type(cls, v):
        """验证评估器类型"""
        valid_types = ["default", "conservative", "aggressive"]
        if v not in valid_types:
            raise ValueError(f'评估器类型必须是{valid_types}之一')
        return v

    @field_validator('interpolation')
    @classmethod
    def validate_interpolation(cls, v):
        """验证插值方式"""
        valid_interpolations = ["linear", "step"]
        if v not in valid_interpolations:
            raise ValueError(f'插值方式必须是{valid_interpolations}之一')
        return v


class BacktestResponse(BaseModel):
    """回测响应"""
    backtest_id: str
    status: str              # "queued", "running", "completed", "failed"
    progress: float          # 0.0 to 1.0
    message: Optional[str] = None
    result: Optional[Dict] = None


class AddStockRequest(BaseModel):
    """添加自选股请求"""
    code: str
    name: str
    market: str = "sz"
    notes: str = ""

    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        """验证股票代码"""
        if not v:
            raise ValueError('股票代码不能为空')
        if not v.isdigit() or len(v) != 6:
            raise ValueError('股票代码必须是6位数字')
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """验证股票名称"""
        if not v or not v.strip():
            raise ValueError('股票名称不能为空')
        return v.strip()

    @field_validator('market')
    @classmethod
    def validate_market(cls, v):
        """验证市场代码"""
        valid_markets = ["sh", "sz"]
        if v not in valid_markets:
            raise ValueError(f'市场代码必须是{valid_markets}之一')
        return v
