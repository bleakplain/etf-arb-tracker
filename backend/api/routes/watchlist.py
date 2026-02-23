"""
自选股管理路由

提供自选股列表的增删查功能
"""

from fastapi import APIRouter, HTTPException
from loguru import logger
from pathlib import Path
from typing import Dict

from backend.api.dependencies import get_monitor, BASE_DIR
from backend.api.models import AddStockRequest

router = APIRouter()


def _load_watchlist_config() -> Dict:
    """加载自选股配置"""
    import yaml

    stocks_file = Path("config/stocks.yaml")
    if stocks_file.exists():
        with open(stocks_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_watchlist_config(config: Dict) -> None:
    """保存自选股配置"""
    import yaml

    stocks_file = Path("config/stocks.yaml")
    with open(stocks_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _clear_monitor_cache() -> None:
    """清除监控器和配置缓存"""
    global _monitor_instance
    from backend.api.dependencies import _monitor_instance
    _monitor_instance = None

    # 清除配置模块的全局缓存
    from config import _config
    if _config is not None:
        import config
        config._config = None


@router.post("/api/watchlist/add")
async def add_to_watchlist(request: AddStockRequest):
    """
    添加股票到自选列表

    Args:
        request: 添加股票请求

    Returns:
        操作结果
    """
    try:
        config = _load_watchlist_config()
        my_stocks = config.get('my_stocks', [])

        # 检查是否已存在
        for stock in my_stocks:
            if stock['code'] == request.code:
                return {
                    "status": "already_exists",
                    "message": f"股票 {request.code} 已在自选列表中"
                }

        # 添加新股票
        new_stock = {
            "code": request.code,
            "name": request.name,
            "market": request.market
        }
        if request.notes:
            new_stock["notes"] = request.notes

        my_stocks.append(new_stock)
        config['my_stocks'] = my_stocks

        # 保存配置
        _save_watchlist_config(config)

        # 清除缓存
        _clear_monitor_cache()

        logger.info(f"已添加股票 {request.code} {request.name} 到自选列表")

        return {
            "status": "success",
            "message": f"已添加 {request.name} 到自选列表"
        }

    except Exception as e:
        logger.error(f"添加自选股失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加失败: {e}")


@router.delete("/api/watchlist/{code}")
async def remove_from_watchlist(code: str):
    """
    从自选列表删除股票

    Args:
        code: 股票代码

    Returns:
        操作结果
    """
    try:
        config = _load_watchlist_config()

        if not config:
            raise HTTPException(status_code=404, detail="配置文件不存在")

        my_stocks = config.get('my_stocks', [])

        # 查找并删除
        original_count = len(my_stocks)
        my_stocks = [s for s in my_stocks if s['code'] != code]

        if len(my_stocks) == original_count:
            raise HTTPException(status_code=404, detail=f"股票 {code} 不在自选列表中")

        config['my_stocks'] = my_stocks

        # 保存配置
        _save_watchlist_config(config)

        # 清除缓存
        _clear_monitor_cache()

        logger.info(f"已从自选列表删除股票 {code}")

        return {
            "status": "success",
            "message": f"已删除股票 {code}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除自选股失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")


@router.get("/api/watchlist")
async def get_watchlist():
    """
    获取自选股列表

    Returns:
        自选股列表
    """
    try:
        config = _load_watchlist_config()
        return {
            "my_stocks": config.get('my_stocks', [])
        }
    except Exception as e:
        logger.error(f"获取自选列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {e}")
