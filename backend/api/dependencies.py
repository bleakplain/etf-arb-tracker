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


class BacktestJobManager:
    """回测任务管理器 - 封装任务状态和线程安全操作"""

    def __init__(self):
        self._jobs: Dict[str, Dict] = {}
        self._lock: AsyncLock = AsyncLock()
        self._thread_lock: ThreadLock = ThreadLock()
        self._repo = get_backtest_repository()

    async def get_job(self, job_id: str) -> Optional[Dict]:
        """获取任务（线程安全）"""
        async with self._lock:
            if job_id in self._jobs:
                return self._jobs[job_id].copy()

        # 从持久化存储加载
        return self._repo.load_job(job_id)

    async def create_job(self, job_id: str, request_data: Dict) -> Dict:
        """创建任务（线程安全）"""
        job = {
            "job_id": job_id,
            "request": request_data,
            "status": "queued",
            "progress": 0.0,
            "result": None,
            "error": None
        }
        async with self._lock:
            self._jobs[job_id] = job
        return job

    def create_progress_callback(self, job_id: str) -> Callable[[float], None]:
        """创建进度回调（线程安全）"""
        def callback(p: float):
            try:
                with self._thread_lock:
                    if job_id in self._jobs:
                        self._jobs[job_id]["progress"] = p
            except Exception:
                pass
        return callback

    async def update_status(
        self,
        job_id: str,
        status: str = None,
        progress: float = None,
        result: Dict = None,
        error: str = None
    ) -> None:
        """更新状态（线程安全）"""
        async with self._lock:
            job = self._jobs.get(job_id)
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
            self._repo.save_job(job_id, job)

    async def delete_job(self, job_id: str) -> None:
        """删除任务"""
        async with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]

    def load_historical_jobs(self) -> int:
        """加载历史任务到内存"""
        try:
            jobs = self._repo.list_jobs(limit=100)
            for job in jobs:
                job_id = job.get("job_id")
                if job_id:
                    self._jobs[job_id] = job
            return len(self._jobs)
        except Exception as e:
            from loguru import logger
            logger.warning(f"加载历史回测任务失败: {e}")
            return 0

    def get_all_jobs(self) -> Dict[str, Dict]:
        """获取所有任务（返回副本避免外部修改）"""
        return self._jobs.copy()


# 全局单例
_backtest_manager = BacktestJobManager()


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
    return _backtest_manager.get_all_jobs()


def get_signal_history() -> list:
    """获取信号历史"""
    return _signal_history


# 向后兼容的函数委托
async def get_backtest_job(backtest_id: str) -> Optional[Dict]:
    """获取回测任务（异步安全）"""
    return await _backtest_manager.get_job(backtest_id)


async def create_backtest_job(job_id: str, request_data: Dict) -> Dict:
    """创建回测任务记录"""
    return await _backtest_manager.create_job(job_id, request_data)


def create_progress_callback(job_id: str) -> Callable[[float], None]:
    """创建进度回调函数（线程安全）"""
    return _backtest_manager.create_progress_callback(job_id)


async def update_backtest_job_status(job_id: str, status: str, progress: float = None, result: Dict = None, error: str = None):
    """更新回测任务状态"""
    await _backtest_manager.update_status(job_id, status, progress, result, error)


async def delete_backtest_job(job_id: str):
    """从内存中删除回测任务"""
    await _backtest_manager.delete_job(job_id)


def load_historical_backtest_jobs():
    """启动时加载历史回测任务到内存"""
    return _backtest_manager.load_historical_jobs()


# 暴露配置实例
def get_config() -> Config:
    """获取配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config.load()
    return _config_instance
