"""
Pytest configuration and shared fixtures

This file contains common fixtures and configuration for all tests.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, time
from typing import Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import strategy modules to trigger plugin registration
# This must be done before any tests run
from backend.arbitrage.cn.strategies.event_detectors import LimitUpDetectorCN
from backend.arbitrage.cn.strategies.fund_selectors import HighestWeightSelector
from backend.arbitrage.cn.strategies.signal_filters import (
    TimeFilterCN,
    LiquidityFilter,
)


# ==================== Fixtures for Data Mocking ====================

@pytest.fixture
def sample_stock_quotes() -> Dict[str, Dict]:
    """Sample stock quotes for testing"""
    return {
        '600519': {
            'code': '600519',
            'name': '贵州茅台',
            'price': 1800.0,
            'change_pct': 0.1001,  # 10.01% - limit up
            'is_limit_up': True,
            'timestamp': '14:00:00',
            'volume': 1000000,
            'amount': 1800000000
        },
        '300750': {
            'code': '300750',
            'name': '宁德时代',
            'price': 256.80,
            'change_pct': 0.2001,  # 20.01% - limit up
            'is_limit_up': True,
            'timestamp': '13:30:00',
            'volume': 5000000,
            'amount': 1284000000
        },
        '000001': {
            'code': '000001',
            'name': '平安银行',
            'price': 12.50,
            'change_pct': 0.015,  # 1.5% - not limit up
            'is_limit_up': False,
            'timestamp': '14:30:00',
            'volume': 8000000,
            'amount': 100000000
        }
    }


@pytest.fixture
def sample_etf_mapping() -> Dict[str, List[Dict]]:
    """Sample stock-to-ETF mapping for testing"""
    return {
        '600519': [
            {'etf_code': '510300', 'etf_name': '沪深300ETF'},
            {'etf_code': '510500', 'etf_name': '中证500ETF'},
        ],
        '300750': [
            {'etf_code': '516160', 'etf_name': '新能源车ETF'},
        ]
    }


@pytest.fixture
def sample_etf_holdings() -> Dict[str, List[Dict]]:
    """Sample ETF top holdings for testing"""
    return {
        '510300': [
            {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.08},
            {'stock_code': '600036', 'stock_name': '招商银行', 'weight': 0.05},
        ],
        '510500': [
            {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.04},
        ],
        '516160': [
            {'stock_code': '300750', 'stock_name': '宁德时代', 'weight': 0.085},
        ]
    }


@pytest.fixture
def sample_etf_quotes() -> Dict[str, Dict]:
    """Sample ETF quotes for testing"""
    return {
        '510300': {
            'code': '510300',
            'name': '沪深300ETF',
            'price': 4.567,
            'change_pct': 1.2,
            'premium': 0.5,
            'volume': 100000000,
            'amount': 456700000
        },
        '510500': {
            'code': '510500',
            'name': '中证500ETF',
            'price': 7.123,
            'change_pct': 0.8,
            'premium': -0.3,
            'volume': 80000000,
            'amount': 569840000
        },
        '516160': {
            'code': '516160',
            'name': '新能源车ETF',
            'price': 1.234,
            'change_pct': 2.5,
            'premium': 1.2,
            'volume': 50000000,
            'amount': 61700000
        }
    }


# ==================== Fixtures for Mock Providers ====================

@pytest.fixture
def mock_quote_fetcher(sample_stock_quotes):
    """Mock IQuoteFetcher implementation"""
    fetcher = Mock()
    fetcher.get_stock_quote.side_effect = lambda code: sample_stock_quotes.get(code)
    fetcher.get_batch_quotes.side_effect = lambda codes: {
        c: sample_stock_quotes.get(c) for c in codes
    }
    fetcher.is_trading_time.return_value = True
    return fetcher


@pytest.fixture
def mock_etf_holder_provider(sample_etf_mapping):
    """Mock IETFHolderProvider implementation"""
    provider = Mock()
    provider.load_mapping.return_value = sample_etf_mapping
    provider.build_stock_etf_mapping.return_value = sample_etf_mapping
    return provider


@pytest.fixture
def mock_etf_holdings_provider(sample_etf_holdings):
    """Mock IETFHoldingsProvider implementation"""
    provider = Mock()

    def get_holdings(etf_code):
        holdings = sample_etf_holdings.get(etf_code, [])
        return {
            'etf_code': etf_code,
            'etf_name': f'ETF_{etf_code}',
            'top_holdings': holdings,
            'total_weight': sum(h['weight'] for h in holdings)
        }

    provider.get_etf_top_holdings.side_effect = get_holdings
    return provider


@pytest.fixture
def mock_etf_quote_provider(sample_etf_quotes):
    """Mock ETF quote provider implementation"""
    provider = Mock()
    provider.get_etf_quote.side_effect = lambda code: sample_etf_quotes.get(code)
    provider.get_etf_batch_quotes.side_effect = lambda codes: {
        c: sample_etf_quotes.get(c) for c in codes
    }
    provider.check_liquidity.return_value = True
    return provider


# ==================== Fixtures for Time Control ====================

@pytest.fixture
def fixed_datetime():
    """Fixture for freezing datetime in tests"""
    frozen_time = datetime(2024, 1, 15, 14, 30, 0)  # Monday 14:30
    with patch('backend.utils.time_utils.datetime') as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield frozen_time


@pytest.fixture
def trading_time():
    """Fixture that sets time to trading hours (14:00)"""
    with patch('backend.utils.time_utils.is_trading_time', return_value=True):
        yield


@pytest.fixture
def non_trading_time():
    """Fixture that sets time to non-trading hours"""
    with patch('backend.utils.time_utils.is_trading_time', return_value=False):
        yield


# ==================== Fixtures for Configuration ====================

@pytest.fixture
def mock_config():
    """Mock configuration object"""
    config = Mock()
    config.strategy = Mock()
    config.strategy.min_weight = 0.05
    config.strategy.scan_interval = 120
    config.strategy.max_signals_per_stock = 3

    config.trading_hours = Mock()
    config.trading_hours.morning_start = time(9, 30)
    config.trading_hours.morning_end = time(11, 30)
    config.trading_hours.afternoon_start = time(13, 0)
    config.trading_hours.afternoon_end = time(15, 0)

    config.data_sources = Mock()
    config.data_sources.primary = 'tencent'
    config.data_sources.fallback = ['eastmoney']

    return config


# ==================== Fixtures for File I/O ====================

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for tests"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def mock_file_io(temp_data_dir):
    """Mock file I/O operations to use temp directory"""
    with patch('backend.arbitrage.cn.DATA_DIR', str(temp_data_dir)):
        yield temp_data_dir


# ==================== Fixtures for External APIs ====================

@pytest.fixture
def mock_http_client():
    """Mock HTTP client for external API calls"""
    with patch('requests.Session') as mock_session:
        session = Mock()
        mock_session.return_value = session

        # Configure successful response
        response = Mock()
        response.status_code = 200
        response.text = ""
        response.json.return_value = {}
        session.get.return_value = response

        yield session


@pytest.fixture
def mock_rate_limiting():
    """Mock rate limiting to speed up tests"""
    with patch('time.sleep'):
        yield


# ==================== Pytest Hooks ====================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "api: API endpoint tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add default markers"""
    for item in items:
        # Mark tests in specific directories
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# ==================== Test Helper Functions ====================

class TestHelpers:
    """Helper functions for tests"""

    @staticmethod
    def assert_signal_valid(signal):
        """Assert that a signal object has required fields"""
        assert signal is not None
        assert hasattr(signal, 'stock_code')
        assert hasattr(signal, 'etf_code')
        assert hasattr(signal, 'confidence')
        assert hasattr(signal, 'risk_level')

    @staticmethod
    def create_limit_up_event(code: str, name: str = None) -> Dict:
        """Create a mock limit-up event"""
        return {
            'code': code,
            'name': name or f'Stock_{code}',
            'price': 100.0,
            'change_pct': 0.1001,
            'is_limit_up': True,
            'timestamp': '14:00:00',
            'volume': 1000000,
            'amount': 100000000
        }

    @staticmethod
    def create_candidate_etf(etf_code: str, weight: float = 0.08, rank: int = 1) -> Dict:
        """Create a mock CandidateETF"""
        return {
            'etf_code': etf_code,
            'etf_name': f'ETF_{etf_code}',
            'weight': weight,
            'rank': rank,
            'top10_ratio': 0.50
        }


@pytest.fixture
def test_helpers():
    """Provide test helper functions"""
    return TestHelpers
