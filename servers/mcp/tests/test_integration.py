#!/usr/bin/env python3
"""
MCP服务器工具集成测试 - 简化版

验证MCP服务器可以正确初始化并与后端模块进行基本交互。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import asyncio
from servers.mcp.etf_arbitrage.server import mcp, get_server_info


class TestServerIntegration:
    """测试服务器与后端集成"""

    def test_backend_modules_import(self):
        """测试后端模块可以正确导入"""
        # 测试关键后端模块导入
        from backend.market.cn.quote_fetcher import CNQuoteFetcher
        from backend.market.cn.etf_quote import CNETFQuoteFetcher
        from backend.signal.db_repository import DBSignalRepository
        from backend.arbitrage.cn.factory import ArbitrageEngineFactory
        from backend.data.backtest_repository import BacktestRepository
        from backend.arbitrage.interfaces import InMemoryMappingRepository

        assert True  # 所有导入成功

    def test_strategy_registry(self):
        """测试策略注册表"""
        from backend.api.dependencies import register_strategies
        from backend.arbitrage.strategy_registry import (
            event_detector_registry,
            fund_selector_registry,
            signal_filter_registry,
        )

        # 注册策略
        register_strategies()

        # 验证策略已注册
        assert 'limit_up_cn' in event_detector_registry.list_names()
        assert 'highest_weight' in fund_selector_registry.list_names()
        assert 'time_filter_cn' in signal_filter_registry.list_names()
        assert 'liquidity_filter' in signal_filter_registry.list_names()

    def test_config_loading(self):
        """测试配置加载"""
        import yaml

        config_path = project_root / "config" / "settings.yaml"
        assert config_path.exists(), "配置文件不存在"

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 验证关键配置
        assert 'strategy' in config
        assert 'trading_hours' in config
        assert config['strategy']['min_weight'] > 0

    def test_database_exists(self):
        """测试数据库文件"""
        db_path = project_root / "data" / "app.db"
        # 数据库可能不存在（首次运行），这是正常的
        assert db_path.parent.exists(), "数据目录不存在"

    def test_tools_have_callable_functions(self):
        """测试所有工具都有可调用的函数"""
        tools = mcp._tool_manager._tools

        for name, tool in tools.items():
            assert hasattr(tool, 'fn'), f"工具 {name} 缺少fn属性"
            assert callable(tool.fn), f"工具 {name} 的fn不可调用"


class TestBackendBridge:
    """测试BackendBridge类"""

    def test_backend_bridge_creation(self):
        """测试BackendBridge可以创建"""
        from servers.mcp.etf_arbitrage.tools.base import BackendBridge

        bridge = BackendBridge()
        assert bridge is not None

    def test_backend_bridge_properties(self):
        """测试BackendBridge属性"""
        from servers.mcp.etf_arbitrage.tools.base import BackendBridge

        bridge = BackendBridge()

        # 验证路径属性
        assert bridge.PROJECT_ROOT == project_root
        assert bridge.CONFIG_DIR == project_root / "config"
        assert bridge.DATA_DIR == project_root / "data"
        assert bridge.get_stocks_path() == bridge.CONFIG_DIR / "stocks.yaml"


class TestToolDefinitions:
    """测试工具定义"""

    def test_market_tools_registered(self):
        """测试市场数据工具已注册"""
        tools = mcp._tool_manager._tools

        market_tools = [
            "etf_arbitrage_get_stock_quote",
            "etf_arbitrage_get_etf_quote",
            "etf_arbitrage_list_limit_up_stocks",
        ]

        for tool_name in market_tools:
            assert tool_name in tools, f"市场数据工具未注册: {tool_name}"

    def test_arbitrage_tools_registered(self):
        """测试套利分析工具已注册"""
        tools = mcp._tool_manager._tools

        arbitrage_tools = [
            "etf_arbitrage_find_related_etfs",
            "etf_arbitrage_analyze_opportunity",
        ]

        for tool_name in arbitrage_tools:
            assert tool_name in tools, f"套利分析工具未注册: {tool_name}"

    def test_signal_tools_registered(self):
        """测试信号管理工具已注册"""
        tools = mcp._tool_manager._tools

        signal_tools = [
            "etf_arbitrage_list_signals",
            "etf_arbitrage_get_signal",
        ]

        for tool_name in signal_tools:
            assert tool_name in tools, f"信号工具未注册: {tool_name}"

    def test_backtest_tools_registered(self):
        """测试回测工具已注册"""
        tools = mcp._tool_manager._tools

        backtest_tools = [
            "etf_arbitrage_run_backtest",
            "etf_arbitrage_get_backtest_result",
            "etf_arbitrage_list_backtests",
        ]

        for tool_name in backtest_tools:
            assert tool_name in tools, f"回测工具未注册: {tool_name}"

    def test_config_tools_registered(self):
        """测试配置工具已注册"""
        tools = mcp._tool_manager._tools

        config_tools = [
            "etf_arbitrage_get_stock_etf_mapping",
            "etf_arbitrage_list_my_stocks",
            "etf_arbitrage_add_my_stock",
            "etf_arbitrage_remove_my_stock",
        ]

        for tool_name in config_tools:
            assert tool_name in tools, f"配置工具未注册: {tool_name}"

    def test_monitor_tools_registered(self):
        """测试监控工具已注册"""
        tools = mcp._tool_manager._tools

        monitor_tools = [
            "etf_arbitrage_get_monitor_status",
            "etf_arbitrage_start_monitor",
            "etf_arbitrage_stop_monitor",
            "etf_arbitrage_trigger_scan",
        ]

        for tool_name in monitor_tools:
            assert tool_name in tools, f"监控工具未注册: {tool_name}"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
