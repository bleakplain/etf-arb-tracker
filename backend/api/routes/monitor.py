"""
监控控制路由

提供监控器状态查询和控制端点
"""

from fastapi import APIRouter, BackgroundTasks
from loguru import logger
import time

from backend.api.dependencies import get_monitor, get_state_manager
from backend.api.models import MonitorStatus
from backend.notification.sender import create_sender_from_config
from datetime import datetime

router = APIRouter()


@router.get("/api/status", response_model=MonitorStatus)
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


@router.post("/api/monitor/scan")
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


@router.post("/api/monitor/start")
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
