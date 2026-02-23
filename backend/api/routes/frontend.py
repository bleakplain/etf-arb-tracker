"""
前端静态文件路由

提供前端页面和静态资源访问
"""

import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse, FileResponse

from backend.api.dependencies import BASE_DIR

router = APIRouter()


@router.get("/")
async def root():
    """根路径 - 重定向到前端页面"""
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))


@router.get("/frontend")
async def frontend():
    """前端页面"""
    return FileResponse(os.path.join(BASE_DIR, "frontend", "index.html"))


@router.get("/frontend/{file_path:path}")
async def frontend_files(file_path: str):
    """
    前端静态文件

    安全措施：防止路径遍历攻击
    """
    # 先检查是否包含明显的路径遍历模式
    if '..' in file_path or file_path.startswith('/'):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    # 规范化路径
    safe_path = os.path.normpath(file_path)

    # 规范化后再次检查
    if '..' in safe_path or safe_path.startswith('/'):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    file_path = os.path.join(BASE_DIR, "frontend", safe_path)

    # 确保解析后的路径仍在frontend目录下
    if not os.path.abspath(file_path).startswith(os.path.abspath(os.path.join(BASE_DIR, "frontend"))):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"detail": "Not Found"})
