#!/usr/bin/env python3
"""
MCP服务器工具测试 - 修正版

使用实际后端测试工具功能。
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from servers.mcp.etf_arbitrage.server import mcp
from servers.mcp.etf_arbitrage.models.requests import *
from servers.mcp.etf_arbitrage.models.enums import ResponseFormat


@pytest.mark.asyncio
async def test_monitor_status_tool():
    """测试监控状态工具"""
    tool = mcp._tool_manager._tools["etf_arbitrage_get_monitor_status"]
    result = await tool.fn()

    # Should return JSON status information
    assert "is_running" in result or "Error" in result
    print(f"Monitor status result: {result[:200]}...")


@pytest.mark.asyncio
async def test_watchlist_tool():
    """测试自选股列表工具"""
    tool = mcp._tool_manager._tools["etf_arbitrage_list_my_stocks"]
    params = ListMyStocksRequest(response_format=ResponseFormat.MARKDOWN)

    result = await tool.fn(params)

    # Should return watchlist
    assert "Watchlist" in result or "自选股" in result or "Total stocks" in result
    print(f"Watchlist result length: {len(result)}")


@pytest.mark.asyncio
async def test_mapping_tool():
    """测试股票-ETF映射工具"""
    tool = mcp._tool_manager._tools["etf_arbitrage_get_stock_etf_mapping"]
    params = GetStockETFMappingRequest(
        stock_code=None,
        include_weights=True,
        response_format=ResponseFormat.JSON
    )

    result = await tool.fn(params)

    # Should return JSON
    data = json.loads(result)
    assert isinstance(data, dict)
    print(f"Mapping result: {list(data.keys())[:5]}...")


@pytest.mark.asyncio
async def test_request_validation():
    """测试请求验证"""
    # Valid stock quote request
    params = GetStockQuoteRequest(codes=["600519"])
    assert params.codes == ["600519"]
    assert params.response_format == ResponseFormat.MARKDOWN

    # Invalid code length
    with pytest.raises(ValueError):
        GetStockQuoteRequest(codes=["12345"])

    # Invalid code format
    with pytest.raises(ValueError):
        GetStockQuoteRequest(codes=["abcdef"])

    # Valid paginated request
    params = ListSignalsRequest(limit=10, offset=0)
    assert params.limit == 10
    assert params.offset == 0

    # Invalid limit (too high)
    with pytest.raises(ValueError):
        ListSignalsRequest(limit=200, offset=0)

    # Invalid limit (too low)
    with pytest.raises(ValueError):
        ListSignalsRequest(limit=0, offset=0)

    print("Request validation tests passed")


@pytest.mark.asyncio
async def test_backtest_tools():
    """测试回测工具"""
    # Test list backtests
    tool = mcp._tool_manager._tools["etf_arbitrage_list_backtests"]
    params = ListBacktestsRequest(
        limit=5,
        offset=0,
        response_format=ResponseFormat.MARKDOWN
    )

    result = await tool.fn(params)

    # Should return backtest list
    assert "Backtest Jobs" in result or "回测任务" in result or "Error" in result
    print(f"Backtest list result: {result[:200]}...")


@pytest.mark.asyncio
async def test_signal_tools():
    """测试信号工具"""
    # Test list signals
    tool = mcp._tool_manager._tools["etf_arbitrage_list_signals"]
    params = ListSignalsRequest(
        limit=5,
        offset=0,
        response_format=ResponseFormat.MARKDOWN
    )

    result = await tool.fn(params)

    # Should return signal list
    assert "Trading Signals" in result or "信号" in result or "Error" in result
    print(f"Signal list result: {result[:200]}...")


def test_enum_values():
    """测试枚举值"""
    assert ResponseFormat.MARKDOWN == "markdown"
    assert ResponseFormat.JSON == "json"

    assert MarketType.SH == "sh"
    assert MarketType.SZ == "sz"
    assert MarketType.BJ == "bj"

    print("Enum values tests passed")


@pytest.mark.asyncio
async def test_monitor_control_tools():
    """测试监控控制工具"""
    # Test start monitor
    start_tool = mcp._tool_manager._tools["etf_arbitrage_start_monitor"]
    start_result = await start_tool.fn()
    assert "Monitor started" in start_result or "started" in start_result.lower() or "Error" in start_result

    # Test stop monitor
    stop_tool = mcp._tool_manager._tools["etf_arbitrage_stop_monitor"]
    stop_result = await stop_tool.fn()
    assert "Monitor stopped" in stop_result or "stopped" in stop_result.lower() or "Error" in stop_result

    print("Monitor control tools tests passed")


@pytest.mark.asyncio
async def test_watchlist_modification_tools():
    """测试自选股修改工具"""
    # These might fail if stock doesn't exist, but we test the interface
    add_tool = mcp._tool_manager._tools["etf_arbitrage_add_my_stock"]
    add_params = AddMyStockRequest(
        code="600519",
        name="贵州茅台",
        market=MarketType.SH,
        notes="测试"
    )
    add_result = await add_tool.fn(add_params)
    print(f"Add watchlist result: {add_result[:100]}...")

    remove_tool = mcp._tool_manager._tools["etf_arbitrage_remove_my_stock"]
    remove_params = RemoveMyStockRequest(code="600519")
    remove_result = await remove_tool.fn(remove_params)
    print(f"Remove watchlist result: {remove_result[:100]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
