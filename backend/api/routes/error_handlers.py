"""
标准错误处理工具

为API路由提供统一的错误处理装饰器
"""

from functools import wraps
from typing import Callable, TypeVar, Any
from fastapi import HTTPException
from loguru import logger

T = TypeVar('T')


def handle_api_errors(operation_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    API错误处理装饰器

    Args:
        operation_name: 操作描述（用于错误消息）

    Example:
        @handle_api_errors("获取自选列表")
        async def get_watchlist():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise  # Re-raise HTTPException as-is
            except Exception as e:
                logger.error(f"{operation_name}失败: {e}")
                raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
        return wrapper
    return decorator


def handle_file_errors(operation_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    文件操作错误处理装饰器

    Args:
        operation_name: 操作描述（用于错误消息）

    Example:
        @handle_file_errors("保存配置")
        async def save_config():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except FileNotFoundError:
                logger.error(f"{operation_name}: 文件不存在")
                raise HTTPException(status_code=404, detail="配置文件不存在")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"{operation_name}失败: {e}")
                raise HTTPException(status_code=500, detail=f"{operation_name}失败: {str(e)}")
        return wrapper
    return decorator
