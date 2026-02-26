"""
Configuration for ETF Arbitrage MCP Server.
"""

from pathlib import Path
from typing import Optional
import os


class Config:
    """MCP Server configuration."""

    # Server identification
    SERVER_NAME = "etf_arbitrage_mcp"
    SERVER_VERSION = "0.1.0"

    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
    CONFIG_DIR = PROJECT_ROOT / "config"
    DATA_DIR = PROJECT_ROOT / "data"
    BACKEND_DIR = PROJECT_ROOT / "backend"

    # Server settings
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 8000

    # Pagination defaults
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100

    # Cache settings
    QUOTE_CACHE_TTL = 60  # seconds
    MAPPING_CACHE_TTL = 3600  # 1 hour

    # Trading hours (China)
    TRADING_HOURS = {
        "morning": {"start": "09:30", "end": "11:30"},
        "afternoon": {"start": "13:00", "end": "15:00"},
    }

    # Default strategy settings
    DEFAULT_MIN_WEIGHT = 0.05  # 5%
    DEFAULT_EVENT_DETECTOR = "limit_up_cn"
    DEFAULT_FUND_SELECTOR = "highest_weight"
    DEFAULT_SIGNAL_FILTERS = ["time_filter_cn", "liquidity_filter"]

    @classmethod
    def get_settings_path(cls) -> Path:
        """Get path to settings.yaml."""
        return cls.CONFIG_DIR / "settings.yaml"

    @classmethod
    def get_stocks_path(cls) -> Path:
        """Get path to stocks.yaml."""
        return cls.CONFIG_DIR / "stocks.yaml"

    @classmethod
    def get_db_path(cls) -> Path:
        """Get path to database."""
        return cls.DATA_DIR / "app.db"

    @classmethod
    def get_mapping_path(cls) -> Path:
        """Get path to stock-ETF mapping cache."""
        return cls.DATA_DIR / "cn_stock_etf_mapping.json"

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        config = cls()
        config.DEFAULT_HOST = os.getenv("MCP_HOST", cls.DEFAULT_HOST)
        config.DEFAULT_PORT = int(os.getenv("MCP_PORT", cls.DEFAULT_PORT))
        return config

    @classmethod
    def get_transport(cls) -> str:
        """Get transport type from environment."""
        return os.getenv("MCP_TRANSPORT", "stdio")

    @classmethod
    def get_log_level(cls) -> str:
        """Get log level from environment."""
        return os.getenv("MCP_LOG_LEVEL", "INFO")
