#!/usr/bin/env python3
"""
MCP服务器基础测试

验证服务器可以正确导入、初始化，并且所有工具都已注册。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from servers.mcp.etf_arbitrage.server import mcp, get_server_info
from servers.mcp.etf_arbitrage.config import Config


class TestServerInitialization:
    """测试服务器初始化"""

    def test_server_import(self):
        """测试服务器可以正确导入"""
        assert mcp is not None
        assert mcp.name == "etf_arbitrage_mcp"

    def test_server_config(self):
        """测试服务器配置"""
        assert Config.SERVER_NAME == "etf_arbitrage_mcp"
        assert Config.SERVER_VERSION == "0.1.0"
        assert Config.DEFAULT_PORT == 8000

    def test_server_info(self):
        """测试服务器信息"""
        info = get_server_info()
        assert "name" in info
        assert "version" in info
        assert "tools" in info
        assert len(info["tools"]) == 18


class TestToolRegistration:
    """测试工具注册"""

    def test_all_tools_registered(self):
        """验证所有工具都已注册"""
        tools = mcp._tool_manager._tools
        expected_tools = [
            # Market Data
            "etf_arbitrage_get_stock_quote",
            "etf_arbitrage_get_etf_quote",
            "etf_arbitrage_list_limit_up_stocks",
            # Arbitrage Analysis
            "etf_arbitrage_find_related_etfs",
            "etf_arbitrage_analyze_opportunity",
            # Signal Management
            "etf_arbitrage_list_signals",
            "etf_arbitrage_get_signal",
            # Backtesting
            "etf_arbitrage_run_backtest",
            "etf_arbitrage_get_backtest_result",
            "etf_arbitrage_list_backtests",
            # Configuration
            "etf_arbitrage_get_stock_etf_mapping",
            "etf_arbitrage_list_my_stocks",
            "etf_arbitrage_add_my_stock",
            "etf_arbitrage_remove_my_stock",
            # Monitor Control
            "etf_arbitrage_get_monitor_status",
            "etf_arbitrage_start_monitor",
            "etf_arbitrage_stop_monitor",
            "etf_arbitrage_trigger_scan",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools, f"工具未注册: {tool_name}"

    def test_tool_has_function(self):
        """验证每个工具都有可调用的函数"""
        tools = mcp._tool_manager._tools

        for tool_name, tool in tools.items():
            assert hasattr(tool, 'fn'), f"工具 {tool_name} 缺少fn属性"
            assert callable(tool.fn), f"工具 {tool_name} 的fn不可调用"

    def test_tool_has_description(self):
        """验证每个工具都有描述"""
        tools = mcp._tool_manager._tools

        for tool_name, tool in tools.items():
            assert hasattr(tool, 'description'), f"工具 {tool_name} 缺少description"
            assert tool.description, f"工具 {tool_name} 的description为空"


class TestToolAnnotations:
    """测试工具注解"""

    def test_read_only_tools_marked(self):
        """验证只读工具正确标记"""
        read_only_tools = [
            "etf_arbitrage_get_stock_quote",
            "etf_arbitrage_get_etf_quote",
            "etf_arbitrage_list_limit_up_stocks",
            "etf_arbitrage_find_related_etfs",
            "etf_arbitrage_analyze_opportunity",
            "etf_arbitrage_list_signals",
            "etf_arbitrage_get_signal",
            "etf_arbitrage_get_backtest_result",
            "etf_arbitrage_list_backtests",
            "etf_arbitrage_get_stock_etf_mapping",
            "etf_arbitrage_list_my_stocks",
            "etf_arbitrage_get_monitor_status",
        ]

        tools = mcp._tool_manager._tools

        for tool_name in read_only_tools:
            tool = tools.get(tool_name)
            assert tool is not None, f"只读工具未找到: {tool_name}"
            # 检查工具注解
            assert hasattr(tool, 'annotations'), f"工具 {tool_name} 缺少annotations"


class TestPydanticModels:
    """测试Pydantic模型"""

    def test_request_models_import(self):
        """测试请求模型可以正确导入"""
        from servers.mcp.etf_arbitrage.models.requests import (
            GetStockQuoteRequest,
            GetETFQuoteRequest,
            ListSignalsRequest,
            RunBacktestRequest,
        )

        # 验证模型可以正确实例化
        request = GetStockQuoteRequest(
            codes=["600519", "000001"],
            response_format="json"
        )
        assert request.codes == ["600519", "000001"]

    def test_enum_values(self):
        """测试枚举值"""
        from servers.mcp.etf_arbitrage.models.enums import (
            ResponseFormat,
            MarketType,
            EventDetectorType,
        )

        assert ResponseFormat.MARKDOWN == "markdown"
        assert ResponseFormat.JSON == "json"
        assert MarketType.SH == "sh"
        assert MarketType.SZ == "sz"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
