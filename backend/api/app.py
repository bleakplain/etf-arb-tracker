"""
Web API服务
提供RESTful接口供前端调用
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, validator
from typing import List, Optional, Dict
import uvicorn
import yaml
from loguru import logger
from datetime import datetime
import os
import sys
import time
from asyncio import Lock, to_thread
from threading import Lock as ThreadLock

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保日志系统已初始化
try:
    from config import get
    get()  # 这会触发日志初始化
except Exception:
    # 如果配置加载失败，使用基本日志配置
    from config.logger import setup, LoggerSettings
    setup(LoggerSettings())

from backend.strategy.limit_monitor import LimitUpMonitor, create_monitor_with_defaults
from backend.notification.sender import create_sender_from_config
from backend.data.limit_up_stocks import LimitUpStocksFetcher
from backend.data.kline import KlineDataFetcher
from backend.data.etf_holdings import ETFHoldingsFetcher
from backend.api.state import get_api_state_manager
from backend.infrastructure.cache import TTLCache
from backend.backtest import BacktestEngine, BacktestConfig
from backend.backtest.clock import TimeGranularity
from backend.backtest.repository import get_backtest_repository
import uuid


# Pydantic模型
class StockInfo(BaseModel):
    """股票信息"""
    code: str
    name: str
    price: float
    change_pct: float
    is_limit_up: bool


class ETFInfo(BaseModel):
    """ETF信息"""
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


class LimitUpStockInfo(BaseModel):
    """涨停股票信息"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: int
    amount: float
    turnover: float
    limit_time: str
    seal_amount: int


# 回测相关模型
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

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """验证日期格式"""
        if not v:
            raise ValueError('日期不能为空')
        try:
            datetime.strptime(v, "%Y%m%d")
        except ValueError:
            raise ValueError('日期格式错误，应为YYYYMMDD格式，例如: 20240101')

        # 限制日期范围（防止极端值）
        min_date = datetime.strptime("20000101", "%Y%m%d")
        max_date = datetime.strptime("20991231", "%Y%m%d")
        input_date = datetime.strptime(v, "%Y%m%d")

        if input_date < min_date:
            raise ValueError('开始日期不能早于20000101')
        if input_date > max_date:
            raise ValueError('结束日期不能晚于20991231')

        return v

    @validator('end_date')
    def validate_date_range(cls, v, values):
        """验证结束日期必须晚于开始日期"""
        if 'start_date' in values:
            start_date = values['start_date']
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

    @validator('granularity')
    def validate_granularity(cls, v):
        """验证时间粒度"""
        valid_granularities = ["daily", "5m", "15m", "30m"]
        if v not in valid_granularities:
            raise ValueError(f'时间粒度必须是{valid_granularities}之一')
        return v

    @validator('min_weight')
    def validate_min_weight(cls, v):
        """验证最小权重"""
        if v is not None:
            if not (0.001 <= v <= 1.0):
                raise ValueError('权重必须在0.001到1.0之间')
        return v

    @validator('evaluator_type')
    def validate_evaluator_type(cls, v):
        """验证评估器类型"""
        valid_types = ["default", "conservative", "aggressive"]
        if v not in valid_types:
            raise ValueError(f'评估器类型必须是{valid_types}之一')
        return v

    @validator('interpolation')
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


# 全局变量
app = FastAPI(
    title="A股涨停ETF溢价监控API",
    description="监控个股涨停，通过ETF获取溢价的辅助工具",
    version="1.0.0"
)

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 状态管理器和监控器实例（使用单例模式）
_api_state_manager = get_api_state_manager()
_monitor_instance: Optional[LimitUpMonitor] = None

# 涨停股缓存
_limit_up_cache = TTLCache(ttl=30, name="limit_up_cache")

# 回测任务存储（带线程安全锁）
_backtest_jobs: Dict[str, Dict] = {}  # backtest_id -> job_info (内存缓存，用于快速访问)
_backtest_lock = Lock()  # 异步锁，保护API端点的并发访问
_backtest_thread_lock = ThreadLock()  # 线程锁，保护progress_callback的同步访问
_backtest_repo = get_backtest_repository()  # 持久化存储仓库


def get_monitor() -> LimitUpMonitor:
    """获取或创建监控器实例"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = create_monitor_with_defaults()
    return _monitor_instance


def get_state_manager():
    """获取状态管理器"""
    return _api_state_manager


@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    logger.info("API服务启动")
    # 加载历史回测任务到内存
    global _backtest_jobs
    try:
        jobs = _backtest_repo.list_jobs(limit=100)
        for job in jobs:
            job_id = job.get("job_id")
            if job_id:
                _backtest_jobs[job_id] = job
        logger.info(f"加载了 {len(_backtest_jobs)} 个历史回测任务")
    except Exception as e:
        logger.warning(f"加载历史回测任务失败: {e}")
    # 不再预加载监控器，改为懒加载
    # 后台线程会自动初始化数据


@app.get("/")
async def root():
    """根路径 - 重定向到前端页面"""
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))


@app.get("/frontend")
async def frontend():
    """前端页面"""
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))


@app.get("/frontend/{file_path:path}")
async def frontend_files(file_path: str):
    """
    前端静态文件

    安全措施：防止路径遍历攻击
    """
    # 先检查是否包含明显的路径遍历模式
    if '..' in file_path or file_path.startswith('/'):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    # 规范化路径
    safe_path = os.path.normpath(file_path)

    # 规范化后再次检查
    if '..' in safe_path or safe_path.startswith('/'):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    file_path = os.path.join(BASE_DIR, "frontend", safe_path)

    # 确保解析后的路径仍在frontend目录下
    if not os.path.abspath(file_path).startswith(os.path.abspath(os.path.join(BASE_DIR, "frontend"))):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


@app.get("/api/status", response_model=MonitorStatus)
async def get_status():
    """
    获取监控状态

    Returns:
        监控状态信息
    """
    mon = get_monitor()
    state = get_state_manager().monitor_state
    is_trading = mon.stock_fetcher.is_trading_time()

    # 统计今天的信号数量
    today = datetime.now().strftime("%Y-%m-%d")
    today_signals = [
        s for s in mon.signal_history
        if s.timestamp.startswith(today)
    ]

    return MonitorStatus(
        is_running=state.is_running,
        is_trading_time=is_trading,
        watch_stocks_count=len(mon.watch_stocks),
        covered_etfs_count=len(mon.get_all_etfs()),
        today_signals_count=len(today_signals),
        last_scan_time=mon.signal_history[-1].timestamp if mon.signal_history else None
    )


@app.get("/api/stocks", response_model=List[StockInfo])
async def get_stocks():
    """
    获取所有自选股的实时行情

    Returns:
        自选股行情列表
    """
    mon = get_monitor()
    stock_codes = [s.code for s in mon.watch_stocks]

    quotes = mon.stock_fetcher.get_batch_quotes(stock_codes)

    result = []
    for code in stock_codes:
        quote = quotes.get(code)
        if quote:
            result.append(StockInfo(
                code=quote['code'],
                name=quote['name'],
                price=quote['price'],
                change_pct=quote['change_pct'],
                is_limit_up=quote['is_limit_up']
            ))

    return result


@app.get("/api/stocks/{code}/related-etfs")
async def get_related_etfs(code: str):
    """
    获取股票相关的ETF列表

    只返回该股票持仓占比 >= 5% 的 ETF，确保策略有效性

    Args:
        code: 股票代码

    Returns:
        相关ETF列表（仅包含持仓>=5%的ETF）
    """
    mon = get_monitor()

    # 使用带真实权重验证的方法，只返回持仓占比 >= 5% 的 ETF
    etfs = mon.find_related_etfs_with_real_weight(code)

    # 如果没有符合条件的ETF，返回空列表
    if not etfs:
        return []

    # 获取ETF实时行情
    etf_codes = [e['etf_code'] for e in etfs]
    quotes = mon.etf_fetcher.get_etf_batch_quotes(etf_codes)

    result = []
    for etf in etfs:
        etf_code = etf['etf_code']
        quote = quotes.get(etf_code)
        if quote:
            result.append({
                "etf_code": etf_code,
                "etf_name": etf['etf_name'],
                "weight": etf['weight'],
                "rank": etf.get('rank', -1),
                "in_top10": etf.get('in_top10', False),
                "category": etf.get('category', '宽基'),
                "price": quote['price'],
                "change_pct": quote['change_pct'],
                "volume": quote['amount'],
                "premium": quote.get('premium')
            })
        else:
            # 即使获取不到行情，也返回基本信息
            result.append({
                "etf_code": etf_code,
                "etf_name": etf['etf_name'],
                "weight": etf['weight'],
                "rank": etf.get('rank', -1),
                "in_top10": etf.get('in_top10', False),
                "category": etf.get('category', '宽基'),
                "price": 0,
                "change_pct": 0,
                "volume": 0,
                "premium": None
            })

    return result


@app.get("/api/signals", response_model=List[SignalResponse])
async def get_signals(limit: int = 20, today_only: bool = True):
    """
    获取信号历史

    Args:
        limit: 返回数量限制
        today_only: 是否只返回今天的信号

    Returns:
        信号列表
    """
    mon = get_monitor()

    signals = mon.signal_history

    if today_only:
        today = datetime.now().strftime("%Y-%m-%d")
        signals = [s for s in signals if s.timestamp.startswith(today)]

    # 按时间倒序
    signals = sorted(signals, key=lambda x: x.timestamp, reverse=True)

    # 限制数量
    signals = signals[:limit]

    return [
        SignalResponse(
            signal_id=s.signal_id,
            timestamp=s.timestamp,
            stock_code=s.stock_code,
            stock_name=s.stock_name,
            stock_price=s.stock_price,
            etf_code=s.etf_code,
            etf_name=s.etf_name,
            etf_price=s.etf_price,
            etf_weight=s.etf_weight,
            confidence=s.confidence,
            risk_level=s.risk_level,
            reason=s.reason
        )
        for s in signals
    ]


@app.post("/api/monitor/scan")
async def manual_scan(background_tasks: BackgroundTasks):
    """
    手动触发一次扫描

    Returns:
        扫描结果
    """
    mon = get_monitor()

    # 在后台执行扫描
    def run_scan():
        signals = mon.scan_all_stocks()
        if signals:
            # 发送通知
            config = mon.config
            sender = create_sender_from_config(config)
            for signal in signals:
                sender.send_signal(signal)
            # 保存信号
            mon.save_signals()

    background_tasks.add_task(run_scan)

    return {
        "status": "success",
        "message": "扫描任务已提交，正在后台执行"
    }


@app.post("/api/monitor/start")
async def start_monitor(background_tasks: BackgroundTasks):
    """
    启动持续监控

    Returns:
        启动结果
    """
    state = get_state_manager().monitor_state

    if not state.start():
        return {"status": "already_running", "message": "监控已在运行中"}

    def run_monitor():
        mon = get_monitor()
        config = mon.config
        sender = create_sender_from_config(config)

        interval = config.get('strategy', {}).get('scan_interval', 60)

        while state.is_running:
            try:
                if mon.stock_fetcher.is_trading_time():
                    signals = mon.scan_all_stocks()
                    if signals:
                        for signal in signals:
                            sender.send_signal(signal)
                        mon.save_signals()
                    state.increment_scan_count()

                time.sleep(interval)

            except Exception as e:
                logger.error(f"监控出错: {e}")
                time.sleep(interval)

    background_tasks.add_task(run_monitor)

    return {
        "status": "started",
        "message": "持续监控已启动"
    }


@app.post("/api/monitor/stop")
async def stop_monitor():
    """
    停止持续监控

    Returns:
        停止结果
    """
    state = get_state_manager().monitor_state

    if not state.stop():
        return {"status": "not_running", "message": "监控未在运行"}

    return {
        "status": "stopped",
        "message": "持续监控已停止"
    }


@app.get("/api/config")
async def get_config():
    """
    获取配置信息

    Returns:
        配置信息（敏感信息已隐藏）
    """
    try:
        with open("config/settings.yaml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 隐藏敏感信息
        if 'notification' in config:
            if 'dingtalk' in config['notification']:
                config['notification']['dingtalk']['webhook'] = "***" if config['notification']['dingtalk'].get('webhook') else ""
                config['notification']['dingtalk']['secret'] = "***" if config['notification']['dingtalk'].get('secret') else ""
            if 'email' in config['notification']:
                config['notification']['email']['password'] = "***"

        return config

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置失败: {e}")


@app.get("/api/mapping")
async def get_stock_etf_mapping():
    """
    获取股票-ETF映射关系

    Returns:
        映射关系字典
    """
    mon = get_monitor()
    return mon.stock_etf_mapping


@app.get("/api/limit-up", response_model=List[LimitUpStockInfo])
async def get_limit_up_stocks():
    """
    获取今日所有涨停股票（带缓存，复用股票行情缓存）

    Returns:
        涨停股票列表
    """
    # 使用TTLCache组件
    def load_limit_up_stocks():
        """加载涨停股数据"""
        fetcher = LimitUpStocksFetcher()

        # 尝试从监控器获取缓存的股票数据
        try:
            mon = get_monitor()
            stock_df = mon.stock_fetcher._get_spot_data()
            stocks = fetcher.get_today_limit_ups(stock_df)
        except Exception as e:
            logger.warning(f"Failed to get cached spot data, using fresh fetch: {e}")
            stocks = fetcher.get_today_limit_ups()

        return [
            LimitUpStockInfo(
                code=s['code'],
                name=s['name'],
                price=s['price'],
                change_pct=s['change_pct'],
                volume=s['volume'],
                amount=s['amount'],
                turnover=s['turnover'],
                limit_time=s['limit_time'],
                seal_amount=s['seal_amount']
            )
            for s in stocks
        ]

    # 使用统一的缓存组件
    return _limit_up_cache.get_or_load("limit_up_stocks", load_limit_up_stocks)


@app.get("/api/stocks/{code}/kline")
async def get_stock_kline(code: str, days: int = 60):
    """
    获取股票K线数据

    Args:
        code: 股票代码
        days: 天数

    Returns:
        K线数据
    """
    fetcher = KlineDataFetcher()
    kline_data = fetcher.get_kline_for_chart(code, days)

    if not kline_data:
        raise HTTPException(status_code=404, detail="无法获取K线数据")

    return kline_data


@app.get("/api/etfs/{code}/kline")
async def get_etf_kline(code: str, days: int = 60):
    """
    获取ETF K线数据

    Args:
        code: ETF代码
        days: 天数

    Returns:
        K线数据
    """
    fetcher = KlineDataFetcher()
    kline_data = fetcher.get_etf_kline(code, days)

    if not kline_data:
        raise HTTPException(status_code=404, detail="无法获取K线数据")

    return kline_data


@app.get("/api/health")
async def health_check():
    """
    健康检查

    Returns:
        健康状态
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/etfs/{code}/holdings")
async def get_etf_holdings(code: str):
    """
    获取ETF的前十大持仓

    Args:
        code: ETF代码

    Returns:
        ETF持仓信息
    """
    fetcher = ETFHoldingsFetcher()
    holdings = fetcher.get_etf_top_holdings(code)

    return {
        "etf_code": holdings['etf_code'],
        "etf_name": holdings['etf_name'],
        "top_holdings": holdings['top_holdings'],
        "total_weight": holdings['total_weight']
    }


@app.get("/api/etfs/categories")
async def get_etf_categories():
    """
    获取所有ETF分类

    Returns:
        ETF分类数据
    """
    fetcher = ETFHoldingsFetcher()
    categories = fetcher.get_all_etfs_by_category()

    return categories


# Pydantic模型用于自选股管理
class AddStockRequest(BaseModel):
    """添加自选股请求"""
    code: str
    name: str
    market: str = "sz"
    notes: str = ""

    @validator('code')
    def validate_code(cls, v):
        """验证股票代码"""
        if not v:
            raise ValueError('股票代码不能为空')
        if not v.isdigit() or len(v) != 6:
            raise ValueError('股票代码必须是6位数字')
        return v

    @validator('name')
    def validate_name(cls, v):
        """验证股票名称"""
        if not v or not v.strip():
            raise ValueError('股票名称不能为空')
        return v.strip()

    @validator('market')
    def validate_market(cls, v):
        """验证市场代码"""
        valid_markets = ["sh", "sz"]
        if v not in valid_markets:
            raise ValueError(f'市场代码必须是{valid_markets}之一')
        return v


def _load_watchlist_config() -> Dict:
    """加载自选股配置"""
    import yaml
    from pathlib import Path

    stocks_file = Path("config/stocks.yaml")
    if stocks_file.exists():
        with open(stocks_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_watchlist_config(config: Dict) -> None:
    """保存自选股配置"""
    import yaml
    from pathlib import Path

    stocks_file = Path("config/stocks.yaml")
    with open(stocks_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _clear_monitor_cache() -> None:
    """清除监控器和配置缓存"""
    global _monitor_instance
    _monitor_instance = None

    # 清除配置模块的全局缓存
    from config import _config
    if _config is not None:
        import config
        config._config = None


@app.post("/api/watchlist/add")
async def add_to_watchlist(request: AddStockRequest):
    """
    添加股票到自选列表

    Args:
        request: 添加股票请求

    Returns:
        操作结果
    """
    try:
        config = _load_watchlist_config()
        my_stocks = config.get('my_stocks', [])

        # 检查是否已存在
        for stock in my_stocks:
            if stock['code'] == request.code:
                return {
                    "status": "already_exists",
                    "message": f"股票 {request.code} 已在自选列表中"
                }

        # 添加新股票
        new_stock = {
            "code": request.code,
            "name": request.name,
            "market": request.market
        }
        if request.notes:
            new_stock["notes"] = request.notes

        my_stocks.append(new_stock)
        config['my_stocks'] = my_stocks

        # 保存配置
        _save_watchlist_config(config)

        # 清除缓存
        _clear_monitor_cache()

        logger.info(f"已添加股票 {request.code} {request.name} 到自选列表")

        return {
            "status": "success",
            "message": f"已添加 {request.name} 到自选列表"
        }

    except Exception as e:
        logger.error(f"添加自选股失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加失败: {e}")


@app.delete("/api/watchlist/{code}")
async def remove_from_watchlist(code: str):
    """
    从自选列表删除股票

    Args:
        code: 股票代码

    Returns:
        操作结果
    """
    try:
        config = _load_watchlist_config()

        if not config:
            raise HTTPException(status_code=404, detail="配置文件不存在")

        my_stocks = config.get('my_stocks', [])

        # 查找并删除
        original_count = len(my_stocks)
        my_stocks = [s for s in my_stocks if s['code'] != code]

        if len(my_stocks) == original_count:
            raise HTTPException(status_code=404, detail=f"股票 {code} 不在自选列表中")

        config['my_stocks'] = my_stocks

        # 保存配置
        _save_watchlist_config(config)

        # 清除缓存
        _clear_monitor_cache()

        logger.info(f"已从自选列表删除股票 {code}")

        return {
            "status": "success",
            "message": f"已删除股票 {code}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除自选股失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")


@app.get("/api/watchlist")
async def get_watchlist():
    """
    获取自选股列表

    Returns:
        自选股列表
    """
    try:
        config = _load_watchlist_config()
        return {
            "my_stocks": config.get('my_stocks', [])
        }
    except Exception as e:
        logger.error(f"获取自选列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {e}")


# _get_recommended_etfs 函数已移除，API现在使用 find_related_etfs_with_real_weight
# 该方法只返回持仓占比 >= 5% 的 ETF，确保策略有效性


# ============ 回测相关API端点 ============

@app.post("/api/backtest/start", response_model=BacktestResponse)
async def start_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    """
    启动回测任务

    返回任务ID用于查询进度

    Args:
        request: 回测请求参数
        background_tasks: FastAPI后台任务

    Returns:
        回测任务响应
    """
    from config import Config

    job_id = str(uuid.uuid4())

    # 创建回测任务记录（线程安全）
    async with _backtest_lock:
        _backtest_jobs[job_id] = {
            "job_id": job_id,
            "request": request.dict(),  # 转换为字典以便序列化
            "status": "queued",
            "progress": 0.0,
            "result": None,
            "error": None
        }

    # 后台执行回测
    async def run_backtest_job():
        try:
            # 更新状态为运行中
            async with _backtest_lock:
                job = _backtest_jobs.get(job_id)
                if not job:
                    logger.error(f"回测任务 {job_id} 不存在")
                    return
                job["status"] = "running"

            # 加载配置
            app_config = Config.load()

            # 将字符串转换为 TimeGranularity 枚举
            granularity_map = {
                "daily": TimeGranularity.DAILY,
                "5m": TimeGranularity.MINUTE_5,
                "15m": TimeGranularity.MINUTE_15,
                "30m": TimeGranularity.MINUTE_30,
            }
            time_granularity = granularity_map.get(request.granularity, TimeGranularity.DAILY)

            # 创建回测配置
            config = BacktestConfig(
                start_date=request.start_date,
                end_date=request.end_date,
                time_granularity=time_granularity,
                min_weight=request.min_weight or app_config.strategy.min_weight,
                evaluator_type=request.evaluator_type,
                interpolation=request.interpolation
            )

            # 应用股票数量限制（用于快速测试）
            stocks = app_config.my_stocks
            etf_codes = [e.code for e in app_config.watch_etfs]

            if request.max_stocks and request.max_stocks > 0:
                stocks = stocks[:request.max_stocks]
                logger.info(f"限制股票数量为 {request.max_stocks} 用于快速测试")

            if request.max_etfs and request.max_etfs > 0:
                etf_codes = etf_codes[:request.max_etfs]
                logger.info(f"限制ETF数量为 {request.max_etfs} 用于快速测试")

            # 创建进度回调（线程安全）
            def progress_callback(p: float):
                # 直接更新进度（回测运行期间不会有并发修改）
                try:
                    with _backtest_thread_lock:
                        job = _backtest_jobs.get(job_id)
                        if job:
                            job["progress"] = p
                except Exception:
                    pass  # 忽略进度更新错误

            # 创建回测引擎
            engine = BacktestEngine(
                config=config,
                stocks=stocks,
                etf_codes=etf_codes,
                app_config=app_config,
                progress_callback=progress_callback
            )

            # 运行回测（在单独的线程中执行，避免阻塞事件循环）
            result = await to_thread(engine.run)

            # 更新完成状态
            async with _backtest_lock:
                job = _backtest_jobs.get(job_id)
                if job:
                    job["result"] = result.to_dict()
                    job["status"] = "completed"
                    job["progress"] = 1.0
                    # 保存到持久化存储
                    _backtest_repo.save_job(job_id, job)

            logger.info(f"回测任务 {job_id} 完成")

        except Exception as e:
            logger.error(f"回测任务 {job_id} 失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 更新失败状态
            try:
                async with _backtest_lock:
                    job = _backtest_jobs.get(job_id)
                    if job:
                        job["status"] = "failed"
                        job["error"] = str(e)
                        # 保存到持久化存储
                        _backtest_repo.save_job(job_id, job)
            except Exception as lock_error:
                logger.error(f"更新回测任务状态失败: {lock_error}")

    background_tasks.add_task(run_backtest_job)

    return BacktestResponse(
        backtest_id=job_id,
        status="queued",
        progress=0.0,
        message="回测任务已加入队列"
    )


@app.get("/api/backtest/{backtest_id}", response_model=BacktestResponse)
async def get_backtest_result(backtest_id: str):
    """
    获取回测结果

    Args:
        backtest_id: 回测任务ID

    Returns:
        回测任务状态和结果
    """
    # 先从内存缓存中获取
    job = _backtest_jobs.get(backtest_id)

    # 如果内存中没有，尝试从持久化存储加载
    if not job:
        job = _backtest_repo.load_job(backtest_id)
        if job:
            # 加载到内存缓存
            _backtest_jobs[backtest_id] = job

    if not job:
        raise HTTPException(status_code=404, detail="Backtest not found")

    # 复制数据以避免在锁外访问
    job_copy = {
        "status": job["status"],
        "progress": job["progress"],
        "error": job.get("error"),
        "result": job.get("result")
    }

    return BacktestResponse(
        backtest_id=backtest_id,
        status=job_copy["status"],
        progress=job_copy["progress"],
        message=job_copy.get("error"),
        result=job_copy.get("result")
    )


@app.get("/api/backtest/{backtest_id}/signals")
async def get_backtest_signals(backtest_id: str):
    """
    获取回测触发的所有信号

    Args:
        backtest_id: 回测任务ID

    Returns:
        信号列表和总数
    """
    # 先从内存获取，没有则从持久化存储加载
    job = _backtest_jobs.get(backtest_id)
    if not job:
        job = _backtest_repo.load_job(backtest_id)
        if job:
            _backtest_jobs[backtest_id] = job

    if not job:
        raise HTTPException(status_code=404, detail="Backtest not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Backtest not completed yet")

    result = job.get("result", {})
    signals = result.get("signals", [])

    return {
        "signals": signals,
        "total": len(signals)
    }


@app.get("/api/backtest/{backtest_id}/statistics")
async def get_backtest_statistics(backtest_id: str):
    """
    获取回测统计信息

    Args:
        backtest_id: 回测任务ID

    Returns:
        统计信息
    """
    # 先从内存获取，没有则从持久化存储加载
    job = _backtest_jobs.get(backtest_id)
    if not job:
        job = _backtest_repo.load_job(backtest_id)
        if job:
            _backtest_jobs[backtest_id] = job

    if not job:
        raise HTTPException(status_code=404, detail="Backtest not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Backtest not completed yet")

    result = job.get("result", {})
    statistics = result.get("statistics", {})

    return statistics


@app.get("/api/backtest")
async def list_backtests():
    """
    获取所有回测任务列表

    Returns:
        回测任务列表
    """
    # 从持久化存储获取所有任务
    jobs = _backtest_repo.list_jobs(limit=100)

    # 格式化返回数据
    result = []
    for job in jobs:
        job_id = job.get("job_id")
        if not job_id:
            continue

        request_data = job.get("request")
        # 处理 request 数据（可能是字典或 Pydantic 模型）
        if isinstance(request_data, dict):
            start_date = request_data.get("start_date")
            end_date = request_data.get("end_date")
            granularity = request_data.get("granularity")
        elif hasattr(request_data, 'dict'):
            req_dict = request_data.dict()
            start_date = req_dict.get("start_date")
            end_date = req_dict.get("end_date")
            granularity = req_dict.get("granularity")
        else:
            # 如果 request 数据格式不对，使用默认值
            start_date = None
            end_date = None
            granularity = None

        result.append({
            "job_id": job_id,
            "status": job.get("status"),
            "progress": job.get("progress", 0.0),
            "start_date": start_date,
            "end_date": end_date,
            "granularity": granularity,
            "modified_time": job.get("modified_time")
        })

    return {"jobs": result}


@app.delete("/api/backtest/{backtest_id}")
async def delete_backtest(backtest_id: str):
    """
    删除回测任务

    Args:
        backtest_id: 回测任务ID

    Returns:
        删除结果
    """
    # 先检查是否存在
    exists_in_memory = backtest_id in _backtest_jobs
    exists_in_repo = _backtest_repo.load_job(backtest_id) is not None

    if not exists_in_memory and not exists_in_repo:
        raise HTTPException(status_code=404, detail="Backtest not found")

    # 从内存中删除
    if exists_in_memory:
        async with _backtest_lock:
            if backtest_id in _backtest_jobs:
                del _backtest_jobs[backtest_id]

    # 从持久化存储中删除（无论是否存在都尝试删除）
    _backtest_repo.delete_job(backtest_id)

    return {
        "status": "success",
        "message": f"Backtest {backtest_id} deleted"
    }


def start_server(host: str = "0.0.0.0", port: int = 8000):
    """
    启动API服务器

    Args:
        host: 监听地址
        port: 监听端口
    """
    logger.info(f"启动API服务器: http://{host}:{port}")
    logger.info(f"API文档: http://{host}:{port}/docs")

    uvicorn.run(
        "backend.api.app:app",
        host=host,
        port=port,
        reload=True,  # 开发模式，生产环境设为False
        log_level="info"
    )


if __name__ == "__main__":
    start_server()
