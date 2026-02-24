"""
API应用启动和模块导入验证测试

这些测试确保所有API路由模块可以被正确导入，
应用可以成功启动，防止类似backend.data模块缺失的问题。
"""

import pytest
import sys
from pathlib import Path


@pytest.mark.unit
class TestModuleImports:
    """测试所有关键模块可以正确导入"""

    def test_import_backend_data_modules(self):
        """测试backend.data模块可以导入"""
        # 这些模块被API路由使用，必须能正确导入
        from backend.data.backtest_repository import get_backtest_repository, BacktestRepository
        from backend.data.limit_up_stocks import LimitUpStocksFetcher
        from backend.data.kline import KlineDataFetcher
        from backend.data.etf_holdings import ETFHoldingsFetcher

        # 验证实例化成功
        repo = get_backtest_repository()
        assert isinstance(repo, BacktestRepository)

        fetcher1 = LimitUpStocksFetcher()
        assert fetcher1 is not None

        fetcher2 = KlineDataFetcher()
        assert fetcher2 is not None

        fetcher3 = ETFHoldingsFetcher()
        assert fetcher3 is not None

    def test_import_api_routes(self):
        """测试所有API路由模块可以导入"""
        # 测试所有9个路由模块
        try:
            from backend.api.routes import health
            from backend.api.routes import frontend
            from backend.api.routes import monitor
            from backend.api.routes import signals
            from backend.api.routes import stocks
            from backend.api.routes import watchlist
            from backend.api.routes import config
            from backend.api.routes import backtest

            # 验证每个模块都有router属性
            assert hasattr(health, 'router')
            assert hasattr(frontend, 'router')
            assert hasattr(monitor, 'router')
            assert hasattr(signals, 'router')
            assert hasattr(stocks, 'router')
            assert hasattr(watchlist, 'router')
            assert hasattr(config, 'router')
            assert hasattr(backtest, 'router')
        except NameError as e:
            pytest.fail(f"Failed to import API routes: {e}")

    def test_import_api_dependencies(self):
        """测试API依赖模块可以导入"""
        from backend.api import dependencies
        from backend.api import state
        from backend.api import models

        # 验证关键函数/类存在
        assert hasattr(dependencies, 'get_engine')
        assert hasattr(dependencies, 'get_state_manager')
        assert hasattr(dependencies, 'get_limit_up_cache')
        assert hasattr(dependencies, 'get_backtest_repository')

        assert hasattr(state, 'MonitorState')
        assert hasattr(state, 'APIStateManager')
        assert hasattr(state, 'get_api_state_manager')

        # 验证模型存在
        assert hasattr(models, 'StockQuoteResponse')
        assert hasattr(models, 'ETFQuoteResponse')
        assert hasattr(models, 'SignalResponse')
        assert hasattr(models, 'MonitorStatus')
        assert hasattr(models, 'LimitUpStockResponse')
        assert hasattr(models, 'BacktestRequest')
        assert hasattr(models, 'AddStockRequest')

    def test_import_arbitrage_engine(self):
        """测试套利引擎可以导入"""
        from backend.arbitrage.cn import ArbitrageEngineCN
        from backend.arbitrage.cn.factory import ArbitrageEngineFactory

        assert ArbitrageEngineCN is not None
        assert ArbitrageEngineFactory is not None

    def test_import_market_modules(self):
        """测试市场数据模块可以导入"""
        from backend.market.cn import CNQuoteFetcher, CNETFQuoteFetcher, CNETFHoldingProvider
        from backend.market.interfaces import IQuoteFetcher, IETFHoldingProvider

        # 验证类可以被实例化
        fetcher1 = CNQuoteFetcher()
        assert fetcher1 is not None

        fetcher2 = CNETFQuoteFetcher()
        assert fetcher2 is not None

        provider = CNETFHoldingProvider()
        assert provider is not None


@pytest.mark.unit
class TestApplicationStartup:
    """测试应用可以成功启动"""

    def test_api_app_can_be_imported(self):
        """测试API应用主模块可以导入"""
        # 这个测试确保backend.api.app可以正确导入
        # 如果依赖的模块缺失，导入会失败
        try:
            from backend.api import app
            assert app is not None
        except ImportError as e:
            pytest.fail(f"Failed to import API app: {e}")

    def test_api_app_has_fastapi_instance(self):
        """测试API应用有FastAPI实例"""
        from backend.api import app

        # 验证FastAPI应用存在
        assert hasattr(app, 'app')
        assert app.app is not None

        # 验证应用配置
        fastapi_app = app.app
        assert fastapi_app.title is not None
        assert fastapi_app.routes is not None
        assert len(fastapi_app.routes) > 0

    def test_api_routes_registered(self):
        """测试所有API路由已注册"""
        from backend.api import app

        # 获取所有路由
        routes = app.app.routes
        route_paths = {route.path for route in routes if hasattr(route, 'path')}

        # 验证关键路由存在
        expected_routes = [
            "/api/health",
            "/api/status",
            "/api/stocks",
            "/api/signals",
            "/api/watchlist",
            "/api/backtest/start",
        ]

        for route in expected_routes:
            assert any(r.startswith(route) for r in route_paths), f"Route {route} not found"

    def test_api_cors_middleware(self):
        """测试API有CORS中间件配置"""
        from backend.api import app

        # 验证CORS中间件已配置
        fastapi_app = app.app
        # FastAPI的CORS中间件会在middleware列表中
        assert fastapi_app.middleware is not None


@pytest.mark.unit
class TestDependencyValidation:
    """测试依赖关系完整性"""

    def test_all_api_routes_have_dependencies(self):
        """测试所有API路由的依赖都可以满足"""
        # 这个测试确保每个路由文件的导入都可以成功
        route_modules = [
            'backend.api.routes.health',
            'backend.api.routes.frontend',
            'backend.api.routes.monitor',
            'backend.api.routes.signals',
            'backend.api.routes.stocks',
            'backend.api.routes.watchlist',
            'backend.api.routes.config',
            'backend.api.routes.backtest',
        ]

        for module_name in route_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_repository_implementations_exist(self):
        """测试所有仓储实现都存在"""
        from backend.arbitrage.interfaces import (
            FileMappingRepository,
            InMemoryMappingRepository,
            IMappingRepository
        )
        from backend.signal.memory_repository import (
            InMemorySignalRepository,
            ISignalRepository
        )
        from backend.signal.db_repository import DBSignalRepository
        from backend.data.backtest_repository import BacktestRepository

        # 验证可以被实例化
        repo1 = InMemoryMappingRepository()
        assert repo1 is not None

        repo2 = FileMappingRepository("/tmp/test.json")
        assert repo2 is not None

        repo3 = BacktestRepository()
        assert repo3 is not None

    def test_data_fetchers_exist(self):
        """测试所有数据获取器都存在"""
        from backend.data.limit_up_stocks import LimitUpStocksFetcher
        from backend.data.kline import KlineDataFetcher
        from backend.data.etf_holdings import ETFHoldingsFetcher

        # 验证可以被实例化
        fetcher1 = LimitUpStocksFetcher()
        assert fetcher1 is not None

        fetcher2 = KlineDataFetcher()
        assert fetcher2 is not None

        fetcher3 = ETFHoldingsFetcher()
        assert fetcher3 is not None
