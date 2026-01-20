"""
Web API服务
提供RESTful接口供前端调用
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import yaml
from loguru import logger
from datetime import datetime
import os
import sys
import time

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.strategy.limit_monitor import LimitUpMonitor, TradingSignal
from backend.notification.sender import create_sender_from_config
from backend.data.limit_up_stocks import LimitUpStocksFetcher
from backend.data.kline import KlineDataFetcher
from backend.data.etf_holdings import ETFHoldingsFetcher


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

# 全局监控器实例
monitor: Optional[LimitUpMonitor] = None
monitor_running = False

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_monitor() -> LimitUpMonitor:
    """获取或创建监控器实例"""
    global monitor
    if monitor is None:
        monitor = LimitUpMonitor()
    return monitor


@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    logger.info("API服务启动")
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
    """前端静态文件"""
    file_path = os.path.join(BASE_DIR, "frontend", file_path)
    if os.path.exists(file_path):
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
    is_trading = mon.stock_fetcher.is_trading_time()

    # 统计今天的信号数量
    today = datetime.now().strftime("%Y-%m-%d")
    today_signals = [
        s for s in mon.signal_history
        if s.timestamp.startswith(today)
    ]

    return MonitorStatus(
        is_running=monitor_running,
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
    stock_codes = [s['code'] for s in mon.watch_stocks]

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
    global monitor_running

    if monitor_running:
        return {"status": "already_running", "message": "监控已在运行中"}

    monitor_running = True

    def run_monitor():
        global monitor_running
        mon = get_monitor()
        config = mon.config
        sender = create_sender_from_config(config)

        interval = config.get('strategy', {}).get('scan_interval', 60)

        while monitor_running:
            try:
                if mon.stock_fetcher.is_trading_time():
                    signals = mon.scan_all_stocks()
                    if signals:
                        for signal in signals:
                            sender.send_signal(signal)
                        mon.save_signals()

                import time
                time.sleep(interval)

            except Exception as e:
                logger.error(f"监控出错: {e}")
                import time
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
    global monitor_running
    monitor_running = False

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


# 涨停股缓存
_limit_up_cache = None
_limit_up_cache_time = None
_LIMIT_UP_CACHE_TTL = 30  # 涨停股缓存30秒


@app.get("/api/limit-up", response_model=List[LimitUpStockInfo])
async def get_limit_up_stocks():
    """
    获取今日所有涨停股票（带缓存）

    Returns:
        涨停股票列表
    """
    global _limit_up_cache, _limit_up_cache_time

    current_time = time.time()

    # 检查缓存
    if _limit_up_cache is not None and (current_time - _limit_up_cache_time) < _LIMIT_UP_CACHE_TTL:
        return _limit_up_cache

    # 获取新数据
    fetcher = LimitUpStocksFetcher()
    stocks = fetcher.get_today_limit_ups()

    result = [
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

    # 更新缓存
    _limit_up_cache = result
    _limit_up_cache_time = current_time

    return result


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


# _get_recommended_etfs 函数已移除，API现在使用 find_related_etfs_with_real_weight
# 该方法只返回持仓占比 >= 5% 的 ETF，确保策略有效性


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
