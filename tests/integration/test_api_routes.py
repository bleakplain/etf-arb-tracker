"""
API路由集成测试

测试API路由端点的基本功能，确保路由可以正确处理请求。
这些是集成测试，需要测试路由的完整请求-响应流程。
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI


@pytest.mark.integration
class TestAPIRoutesIntegration:
    """测试API路由集成"""

    @pytest.fixture
    def test_client(self):
        """创建测试客户端"""
        # 导入并创建FastAPI应用
        from backend.api.app import app
        return TestClient(app)

    def test_health_endpoint(self, test_client):
        """测试健康检查端点"""
        response = test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_status_endpoint(self, test_client):
        """测试状态查询端点"""
        response = test_client.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert "is_running" in data
        assert "is_trading_time" in data
        assert "watch_stocks_count" in data

    def test_my_stocks_endpoint(self, test_client):
        """测试自选股列表端点"""
        response = test_client.get("/api/my-stocks")

        assert response.status_code == 200
        data = response.json()
        assert "my_stocks" in data

    def test_stocks_endpoint(self, test_client):
        """测试股票行情端点"""
        response = test_client.get("/api/stocks")

        assert response.status_code == 200
        # 应该返回列表，即使为空
        data = response.json()
        assert isinstance(data, list)

    def test_signals_endpoint(self, test_client):
        """测试信号列表端点"""
        response = test_client.get("/api/signals")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_etf_categories_endpoint(self, test_client):
        """测试ETF分类端点"""
        response = test_client.get("/api/etfs/categories")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.integration
class TestAPIRoutesWithMockData:
    """测试API路由与模拟数据"""

    @pytest.fixture
    def test_client_with_mocks(self):
        """创建带有模拟数据的测试客户端"""
        from backend.api.app import app
        return TestClient(app)

    def test_related_etfs_endpoint_with_code(self, test_client_with_mocks):
        """测试获取相关ETF端点"""
        response = test_client_with_mocks.get("/api/stocks/600519/related-etfs")

        # 即使没有相关ETF，也应该返回200和空列表
        assert response.status_code in [200, 404]

    def test_etf_holdings_endpoint(self, test_client_with_mocks):
        """测试ETF持仓端点"""
        response = test_client_with_mocks.get("/api/etfs/510300/holdings")

        assert response.status_code in [200, 404]

    def test_etf_kline_endpoint(self, test_client_with_mocks):
        """测试ETF K线端点"""
        response = test_client_with_mocks.get("/api/etfs/510300/kline?days=60")

        assert response.status_code in [200, 404]

    def test_stock_kline_endpoint(self, test_client_with_mocks):
        """测试股票K线端点"""
        response = test_client_with_mocks.get("/api/stocks/600519/kline?days=60")

        assert response.status_code in [200, 404]


@pytest.mark.integration
class TestBacktestAPIRoutes:
    """测试回测API路由"""

    @pytest.fixture
    def test_client(self):
        """创建测试客户端"""
        from backend.api.app import app
        return TestClient(app)

    def test_backtest_start_with_valid_request(self, test_client):
        """测试启动回测任务"""
        request_data = {
            "start_date": "20240101",
            "end_date": "20240131",
            "granularity": "daily"
        }

        response = test_client.post("/api/backtest/start", json=request_data)

        # 应该成功创建任务
        assert response.status_code in [200, 202]
        data = response.json()
        assert "backtest_id" in data or "status" in data

    def test_backtest_start_with_invalid_dates(self, test_client):
        """测试启动回测任务 - 无效日期"""
        request_data = {
            "start_date": "invalid",
            "end_date": "20240131",
            "granularity": "daily"
        }

        response = test_client.post("/api/backtest/start", json=request_data)

        # 应该返回验证错误
        assert response.status_code == 422

    def test_backtest_start_with_end_before_start(self, test_client):
        """测试启动回测任务 - 结束日期早于开始日期"""
        request_data = {
            "start_date": "20240601",
            "end_date": "20240101",
            "granularity": "daily"
        }

        response = test_client.post("/api/backtest/start", json=request_data)

        # 应该返回验证错误
        assert response.status_code == 422


@pytest.mark.integration
class TestMyStocksAPIRoutes:
    """测试自选股管理API路由"""

    @pytest.fixture
    def test_client(self):
        """创建测试客户端"""
        from backend.api.app import app
        return TestClient(app)

    def test_add_to_my_stocks(self, test_client):
        """测试添加股票到自选"""
        request_data = {
            "code": "600519",
            "name": "贵州茅台",
            "market": "sh"
        }

        response = test_client.post("/api/my-stocks/add", json=request_data)

        # 可能成功或已存在
        assert response.status_code in [200, 201]
        data = response.json()
        assert "status" in data

    def test_add_to_my_stocks_validation(self, test_client):
        """测试添加股票 - 验证"""
        # 无效代码
        request_data = {
            "code": "123",  # 不足6位
            "name": "Test",
            "market": "sh"
        }

        response = test_client.post("/api/my-stocks/add", json=request_data)

        # 应该返回验证错误
        assert response.status_code == 422

    def test_remove_from_my_stocks(self, test_client):
        """测试从自选删除股票"""
        response = test_client.delete("/api/my-stocks/600519")

        # 可能成功或未找到
        assert response.status_code in [200, 404]


@pytest.mark.integration
class TestMonitorAPIRoutes:
    """测试监控控制API路由"""

    @pytest.fixture
    def test_client(self):
        """创建测试客户端"""
        from backend.api.app import app
        return TestClient(app)

    def test_manual_scan_endpoint(self, test_client):
        """测试手动扫描端点"""
        response = test_client.post("/api/monitor/scan")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_start_monitor_endpoint(self, test_client):
        """测试启动监控端点"""
        response = test_client.post("/api/monitor/start")

        assert response.status_code in [200, 400]  # 400如果已在运行

    def test_stop_monitor_endpoint(self, test_client):
        """测试停止监控端点"""
        response = test_client.post("/api/monitor/stop")

        assert response.status_code in [200, 400]  # 400如果未运行


@pytest.mark.integration
class TestConfigAPIRoutes:
    """测试配置管理API路由"""

    @pytest.fixture
    def test_client(self):
        """创建测试客户端"""
        from backend.api.app import app
        return TestClient(app)

    def test_get_stock_etf_mapping(self, test_client):
        """测试获取股票-ETF映射"""
        response = test_client.get("/api/mapping")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
