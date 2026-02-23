"""
监控控制路由

提供监控器状态查询和控制端点
"""

from fastapi import APIRouter, BackgroundTasks
from loguru import logger
import time

from backend.api.dependencies import get_engine, get_state_manager, get_config
from backend.api.models import MonitorStatus
from backend.signal.sender import create_sender_from_config
from datetime import datetime

router = APIRouter()


@router.get("/api/status", response_model=MonitorStatus)
async def get_status():
    """
    获取监控状态

    Returns:
        监控状态信息
    """
    engine = get_engine()
    state = get_state_manager().monitor_state
    is_trading = engine.stock_fetcher.is_trading_time()

    # 统计今天的信号数量
    today = datetime.now().strftime("%Y-%m-%d")
    today_signals = [
        s for s in engine.signal_history
        if s.timestamp.startswith(today)
    ]

    return MonitorStatus(
        is_running=state.is_running,
        is_trading_time=is_trading,
        watch_stocks_count=len(engine.watch_stocks),
        covered_etfs_count=len(engine.get_all_fund_codes()),
        today_signals_count=len(today_signals),
        last_scan_time=engine.signal_history[-1].timestamp if engine.signal_history else None
    )


@router.post("/api/monitor/scan")
async def manual_scan(background_tasks: BackgroundTasks):
    """
    手动触发一次扫描

    Returns:
        扫描结果
    """
    engine = get_engine()
    config = get_config()

    # 在后台执行扫描
    def run_scan():
        result = engine.scan_all()
        if result.signals:
            # 发送通知
            sender = create_sender_from_config(config)
            for signal in result.signals:
                sender.send_signal(signal)

    background_tasks.add_task(run_scan)

    return {
        "status": "success",
        "message": "扫描任务已提交，正在后台执行"
    }


@router.post("/api/monitor/start")
async def start_monitor(background_tasks: BackgroundTasks):
    """
    启动持续监控

    Returns:
        启动结果
    """
    state = get_state_manager().monitor_state
    config = get_config()

    if not state.start():
        return {"status": "already_running", "message": "监控已在运行中"}

    def run_monitor():
        engine = get_engine()
        sender = create_sender_from_config(config)

        interval = config.strategy.scan_interval

        while state.is_running:
            try:
                if engine.stock_fetcher.is_trading_time():
                    result = engine.scan_all()
                    if result.signals:
                        for signal in result.signals:
                            sender.send_signal(signal)
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


@router.post("/api/monitor/stop")
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
