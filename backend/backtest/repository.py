"""
回测结果持久化存储仓库

支持回测结果的保存、加载和查询
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from loguru import logger


class DateTimeEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理datetime对象"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class BacktestRepository:
    """
    回测结果仓库

    将回测结果持久化存储到文件系统
    """

    def __init__(self, storage_dir: str = "data/backtest_results"):
        """
        初始化仓库

        Args:
            storage_dir: 存储目录路径
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"回测结果仓库初始化完成，存储目录: {self.storage_dir}")

    def _get_job_file_path(self, job_id: str) -> Path:
        """获取任务文件路径"""
        return self.storage_dir / f"{job_id}.json"

    def save_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        保存回测任务数据

        Args:
            job_id: 任务ID
            job_data: 任务数据

        Returns:
            是否保存成功
        """
        try:
            file_path = self._get_job_file_path(job_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(job_data, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
            logger.debug(f"回测任务 {job_id} 已保存到 {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存回测任务 {job_id} 失败: {e}")
            return False

    def load_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        加载回测任务数据

        Args:
            job_id: 任务ID

        Returns:
            任务数据，如果不存在则返回 None
        """
        try:
            file_path = self._get_job_file_path(job_id)
            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            logger.debug(f"回测任务 {job_id} 已从 {file_path} 加载")
            return job_data
        except Exception as e:
            logger.error(f"加载回测任务 {job_id} 失败: {e}")
            return None

    def delete_job(self, job_id: str) -> bool:
        """
        删除回测任务数据

        Args:
            job_id: 任务ID

        Returns:
            是否删除成功
        """
        try:
            file_path = self._get_job_file_path(job_id)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"回测任务 {job_id} 已删除")
                return True
            return False
        except Exception as e:
            logger.error(f"删除回测任务 {job_id} 失败: {e}")
            return False

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        列出所有回测任务

        Args:
            limit: 最大返回数量

        Returns:
            任务列表
        """
        try:
            jobs = []
            for file_path in sorted(self.storage_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                if len(jobs) >= limit:
                    break

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        job_data = json.load(f)
                    # 添加文件修改时间
                    job_data["modified_time"] = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    jobs.append(job_data)
                except Exception as e:
                    logger.warning(f"读取回测任务文件 {file_path} 失败: {e}")

            return jobs
        except Exception as e:
            logger.error(f"列出回测任务失败: {e}")
            return []

    def get_job_count(self) -> int:
        """获取任务总数"""
        try:
            return len(list(self.storage_dir.glob("*.json")))
        except Exception:
            return 0

    def clean_old_jobs(self, keep_days: int = 30) -> int:
        """
        清理旧任务

        Args:
            keep_days: 保留天数

        Returns:
            清理的任务数量
        """
        try:
            import time
            cutoff_time = time.time() - (keep_days * 24 * 60 * 60)
            cleaned = 0

            for file_path in self.storage_dir.glob("*.json"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    cleaned += 1
                    logger.info(f"删除过期回测任务: {file_path.name}")

            if cleaned > 0:
                logger.info(f"清理了 {cleaned} 个过期回测任务")

            return cleaned
        except Exception as e:
            logger.error(f"清理旧任务失败: {e}")
            return 0


# 全局单例
_repository_instance: Optional[BacktestRepository] = None


def get_backtest_repository() -> BacktestRepository:
    """获取回测结果仓库单例"""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = BacktestRepository()
    return _repository_instance
