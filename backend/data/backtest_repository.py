"""
回测任务仓储

管理回测任务的持久化
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


class BacktestRepository:
    """回测任务仓储"""

    def __init__(self, storage_dir: str = "data/backtest_results"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_job(self, job_id: str, job_data: Dict) -> bool:
        """保存回测任务"""
        try:
            filepath = self.storage_dir / f"{job_id}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(job_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存回测任务失败: {e}")
            return False

    def load_job(self, job_id: str) -> Optional[Dict]:
        """加载回测任务"""
        try:
            filepath = self.storage_dir / f"{job_id}.json"
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载回测任务失败: {e}")
        return None

    def list_jobs(self, limit: int = 100) -> List[Dict]:
        """列出所有回测任务"""
        jobs = []
        try:
            for filepath in sorted(self.storage_dir.glob("*.json"), reverse=True)[:limit]:
                with open(filepath, 'r', encoding='utf-8') as f:
                    jobs.append(json.load(f))
        except Exception as e:
            logger.error(f"列出回测任务失败: {e}")
        return jobs

    def delete_job(self, job_id: str) -> bool:
        """删除回测任务"""
        try:
            filepath = self.storage_dir / f"{job_id}.json"
            if filepath.exists():
                filepath.unlink()
                return True
        except Exception as e:
            logger.error(f"删除回测任务失败: {e}")
        return False


# 全局仓储实例
_repository: Optional[BacktestRepository] = None


def get_backtest_repository() -> BacktestRepository:
    """获取回测仓储单例"""
    global _repository
    if _repository is None:
        _repository = BacktestRepository()
    return _repository
