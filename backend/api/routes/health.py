"""
健康检查路由

提供系统健康状态检查端点
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/api/health")
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
