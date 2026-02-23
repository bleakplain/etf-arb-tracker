"""
配置和插件路由

提供配置信息、股票-ETF映射、插件列表、策略列表等端点
"""

from fastapi import APIRouter, HTTPException
import yaml

router = APIRouter()


@router.get("/api/config")
async def get_config():
    """
    获取配置信息

    Returns:
        配置信息（敏感信息已隐藏）
    """
    try:
        with open("config/settings.yaml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 隐藏敏感信息
        if 'notification' in config:
            if 'dingtalk' in config['notification']:
                config['notification']['dingtalk']['webhook'] = "***" if config['notification']['dingtalk'].get('webhook') else ""
                config['notification']['dingtalk']['secret'] = "***" if config['notification']['dingtalk'].get('secret') else ""
            if 'email' in config['notification']:
                config['notification']['email']['password'] = "***"

        return config

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置失败: {e}")


@router.get("/api/mapping")
async def get_stock_etf_mapping():
    """
    获取股票-ETF映射关系

    Returns:
        映射关系字典
    """
    from backend.api.dependencies import get_engine
    engine = get_engine()
    return engine.get_security_fund_mapping()


@router.get("/api/plugins")
async def list_plugins():
    """
    列出所有已注册的插件

    Returns:
        插件列表和元数据
    """
    from backend.core.plugin_manager import list_all_plugins

    return list_all_plugins()


@router.get("/api/plugins/stats")
async def get_plugin_stats():
    """
    获取插件统计信息

    Returns:
        插件统计
    """
    from backend.core.plugin_manager import get_plugin_stats

    return get_plugin_stats()


@router.get("/api/strategies")
async def list_strategies():
    """
    列出所有已注册的策略

    Returns:
        策略列表和元数据 (事件检测、基金选择、信号过滤)
    """
    from backend.arbitrage.strategy_registry import strategy_manager

    return strategy_manager.get_strategy_summary()


@router.get("/api/strategies/validate")
async def validate_strategy_combination(
    event_detector: str = "limit_up",
    fund_selector: str = "highest_weight",
    filters: str = "time_filter,liquidity_filter"
):
    """
    验证策略组合是否有效

    Args:
        event_detector: 事件检测策略名称
        fund_selector: 基金选择策略名称
        filters: 过滤策略名称列表（逗号分隔）

    Returns:
        {
            "valid": bool,
            "errors": [str]
        }
    """
    from backend.arbitrage.strategy_registry import strategy_manager

    filter_list = [f.strip() for f in filters.split(",") if f.strip()]

    is_valid, errors = strategy_manager.validate_strategy_combination(
        event_detector, fund_selector, filter_list
    )

    return {
        "valid": is_valid,
        "errors": errors
    }
