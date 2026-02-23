"""
API依赖管理

管理API的全局状态、单例和辅助函数
"""

import os
from typing import Optional, Dict, Callable
from threading import Lock as ThreadLock
from asyncio import Lock as AsyncLock

from backend.api.state import get_api_state_manager
from backend.utils.cache_utils import TTLCache
from backend.data.backtest_repository import get_backtest_repository
from backend.arbitrage.cn import ArbitrageEngineCN
from backend.arbitrage.cn.factory import ArbitrageEngineFactory
from backend.market.cn.quote_fetcher import CNQuoteFetcher
from backend.market.cn.etf_holding_provider import CNETFHoldingProvider
from backend.market.cn.etf_quote import CNETFQuoteFetcher
from config import Config

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 状态管理器
_api_state_manager = get_api_state_manager()

# 套利引擎实例（单例）
_engine_instance: Optional[ArbitrageEngineCN] = None
_config_instance: Optional[Config] = None
_signal_history: list = []

# 涨停股缓存
_limit_up_cache = TTLCache(ttl=30, name="limit_up_cache")

# 回测任务存储（带线程安全锁）
_backtest_jobs: Dict[str, Dict] = {}
_backtest_lock: AsyncLock = Lock()
_backtest_thread_lock = ThreadLock()
_backtest_repo = get_backtest_repository()


def get_engine() -> ArbitrageEngineCN:
    """获取或创建套利引擎实例"""
    global _engine_instance, _config_instance
    if _engine_instance is None:
        _config_instance = Config.load()
        _engine_instance = _create_engine(_config_instance)
    return _engine_instance


def _create_engine(config: Config) -> ArbitrageEngineCN:
    """创建套利引擎"""
    quote_fetcher = CNQuoteFetcher()
    etf_holder_provider = CNETFHoldingProvider()
    etf_holdings_provider = CNETFHoldingProvider()
    etf_quote_provider = CNETFQuoteFetcher()

    return ArbitrageEngineFactory.create_engine(
        quote_fetcher=quote_fetcher,
        etf_holder_provider=etf_holder_provider,
        etf_holdings_provider=etf_holdings_provider,
        etf_quote_provider=etf_quote_provider,
        config=config
    )


def get_state_manager():
    """获取状态管理器"""
    return _api_state_manager


def get_limit_up_cache():
    """获取涨停股缓存"""
    return _limit_up_cache


def get_backtest_jobs():
    """获取回测任务字典"""
    return _backtest_jobs


def get_signal_history() -> list:
    """获取信号历史"""
    return _signal_history


async def get_backtest_job(backtest_id: str) -> Optional[Dict]:
    """获取回测任务（异步安全）"""
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
    """创建进度回调函数（线程安全）"""
    def progress_callback(p: float):
        try:
            with _backtest_thread_lock:
                job = _backtest_jobs.get(job_id)
                if job:
                    job["progress"] = p
        except Exception:
            pass
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


def Lock() -> AsyncLock:
    """创建异步锁"""
    return AsyncLock()


# 向后兼容的别名
def get_monitor() -> ArbitrageEngineCN:
    """获取引擎实例（向后兼容）"""
    return get_engine()


# 暴露配置实例
def get_config() -> Config:
    """获取配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config.load()
    return _config_instance
