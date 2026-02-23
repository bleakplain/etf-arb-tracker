"""
回测路由

提供回测任务的创建、查询、管理和删除功能
"""

import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger
from asyncio import to_thread

from backend.api.dependencies import (
    get_backtest_job,
    create_backtest_job,
    update_backtest_job_status,
    delete_backtest_job,
    create_progress_callback,
    get_backtest_jobs,
)
from backend.api.models import BacktestRequest, BacktestResponse
from backend.data.backtest_repository import get_backtest_repository
from backend.backtest import CNBacktestEngine as BacktestEngine, BacktestConfig
from backend.backtest.models import TimeGranularity

router = APIRouter()
_backtest_repo = get_backtest_repository()


@router.post("/api/backtest/start", response_model=BacktestResponse)
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
    await create_backtest_job(job_id, request.dict())

    # 后台执行回测
    async def run_backtest_job():
        try:
            # 更新状态为运行中
            await update_backtest_job_status(job_id, "running")

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
            progress_callback = create_progress_callback(job_id)

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
            await update_backtest_job_status(
                job_id,
                "completed",
                progress=1.0,
                result=result.to_dict()
            )

            logger.info(f"回测任务 {job_id} 完成")

        except Exception as e:
            logger.error(f"回测任务 {job_id} 失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 更新失败状态
            await update_backtest_job_status(job_id, "failed", error=str(e))

    background_tasks.add_task(run_backtest_job)

    return BacktestResponse(
        backtest_id=job_id,
        status="queued",
        progress=0.0,
        message="回测任务已加入队列"
    )


@router.get("/api/backtest/{backtest_id}", response_model=BacktestResponse)
async def get_backtest_result(backtest_id: str):
    """
    获取回测结果

    Args:
        backtest_id: 回测任务ID

    Returns:
        回测任务状态和结果
    """
    job = await get_backtest_job(backtest_id)

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


@router.get("/api/backtest/{backtest_id}/signals")
async def get_backtest_signals(backtest_id: str):
    """
    获取回测触发的所有信号

    Args:
        backtest_id: 回测任务ID

    Returns:
        信号列表和总数
    """
    job = await get_backtest_job(backtest_id)

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


@router.get("/api/backtest/{backtest_id}/statistics")
async def get_backtest_statistics(backtest_id: str):
    """
    获取回测统计信息

    Args:
        backtest_id: 回测任务ID

    Returns:
        统计信息
    """
    job = await get_backtest_job(backtest_id)

    if not job:
        raise HTTPException(status_code=404, detail="Backtest not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Backtest not completed yet")

    result = job.get("result", {})
    statistics = result.get("statistics", {})

    return statistics


@router.get("/api/backtest")
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


@router.delete("/api/backtest/{backtest_id}")
async def delete_backtest(backtest_id: str):
    """
    删除回测任务

    Args:
        backtest_id: 回测任务ID

    Returns:
        删除结果
    """
    # 先检查是否存在
    jobs = get_backtest_jobs()
    exists_in_memory = backtest_id in jobs
    exists_in_repo = _backtest_repo.load_job(backtest_id) is not None

    if not exists_in_memory and not exists_in_repo:
        raise HTTPException(status_code=404, detail="Backtest not found")

    # 从内存中删除
    if exists_in_memory:
        await delete_backtest_job(backtest_id)

    # 从持久化存储中删除（无论是否存在都尝试删除）
    _backtest_repo.delete_job(backtest_id)

    return {
        "status": "success",
        "message": f"Backtest {backtest_id} deleted"
    }
