"""
API依赖管理

管理API的全局状态、单例和辅助函数
"""

import os
from typing import Optional, Dict, Callable
from threading import Lock as ThreadLock
from asyncio import Lock as AsyncLock

from backend.market.service.limit_monitor import LimitUpMonitor, create_monitor_with_defaults
from backend.api.state import get_api_state_manager
from backend.utils.cache_utils import TTLCache
from backend.data.backtest_repository import get_backtest_repository

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 状态管理器和监控器实例（使用单例模式）
_api_state_manager = get_api_state_manager()
_monitor_instance: Optional[LimitUpMonitor] = None

# 涨停股缓存
_limit_up_cache = TTLCache(ttl=30, name="limit_up_cache")

# 回测任务存储（带线程安全锁）
_backtest_jobs: Dict[str, Dict] = {}  # backtest_id -> job_info (内存缓存，用于快速访问)
_backtest_lock: AsyncLock = Lock()  # 异步锁，保护API端点的并发访问
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


def get_limit_up_cache():
    """获取涨停股缓存"""
    return _limit_up_cache


def get_backtest_jobs():
    """获取回测任务字典（用于内部访问）"""
    return _backtest_jobs


async def get_backtest_job(backtest_id: str) -> Optional[Dict]:
    """
    获取回测任务（异步安全）

    先从内存缓存中获取，如果没有则从持久化存储加载
    """
    # 先从内存获取
    job = _backtest_jobs.get(backtest_id)
    if not job:
        job = _backtest_repo.load_job(backtest_id)
        if job:
            _backtest_jobs[backtest_id] = job
    return job


async def create_backtest_job(job_id: str, request_data: Dict) -> Dict:
    """创建回测任务记录"""
    job = {
        "job_id": job_id,
        "request": request_data,
        "status": "queued",
        "progress": 0.0,
        "result": None,
        "error": None
    }
    async with _backtest_lock:
        _backtest_jobs[job_id] = job
    return job


def create_progress_callback(job_id: str) -> Callable[[float], None]:
    """
    创建进度回调函数（线程安全）

    用于回测过程中更新进度
    """
    def progress_callback(p: float):
        try:
            with _backtest_thread_lock:
                job = _backtest_jobs.get(job_id)
                if job:
                    job["progress"] = p
        except Exception:
            pass  # 忽略进度更新错误
    return progress_callback


async def update_backtest_job_status(job_id: str, status: str, progress: float = None, result: Dict = None, error: str = None):
    """更新回测任务状态"""
    async with _backtest_lock:
        job = _backtest_jobs.get(job_id)
        if not job:
            return
        if status:
            job["status"] = status
        if progress is not None:
            job["progress"] = progress
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error

        # 保存到持久化存储
        _backtest_repo.save_job(job_id, job)


async def delete_backtest_job(job_id: str):
    """从内存中删除回测任务"""
    async with _backtest_lock:
        if job_id in _backtest_jobs:
            del _backtest_jobs[job_id]


def load_historical_backtest_jobs():
    """启动时加载历史回测任务到内存"""
    global _backtest_jobs
    try:
        jobs = _backtest_repo.list_jobs(limit=100)
        for job in jobs:
            job_id = job.get("job_id")
            if job_id:
                _backtest_jobs[job_id] = job
        return len(_backtest_jobs)
    except Exception as e:
        from loguru import logger
        logger.warning(f"加载历史回测任务失败: {e}")
        return 0


# 创建异步锁的辅助函数
def Lock() -> AsyncLock:
    """创建异步锁"""
    return AsyncLock()
