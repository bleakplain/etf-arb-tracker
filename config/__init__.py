"""
配置模块

统一加载和管理所有配置项
"""

import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from config.logger import LoggerSettings, setup
from config.strategy import StrategySettings, TradingHours, RiskControlSettings, SignalEvaluationConfig
from config.alert import AlertSettings


@dataclass
class DataSource:
    """数据源配置"""

    name: str
    url: str

    @classmethod
    def from_dict(cls, data: dict) -> "DataSource":
        return cls(name=data["name"], url=data["url"])


@dataclass
class DataSourcesSettings:
    """数据源设置"""

    quote: list = None
    holdings: list = None

    def __post_init__(self):
        if self.quote is None:
            self.quote = []
        if self.holdings is None:
            self.holdings = []

    @classmethod
    def from_dict(cls, data: dict) -> "DataSourcesSettings":
        quote = [DataSource.from_dict(d) for d in data.get("quote", [])]
        holdings = [DataSource.from_dict(d) for d in data.get("holdings", [])]
        return cls(quote=quote, holdings=holdings)


@dataclass
class DatabaseSettings:
    """数据库设置"""

    path: str = "data/monitor.db"

    @classmethod
    def from_dict(cls, data: dict) -> "DatabaseSettings":
        return cls(path=data.get("path", "data/monitor.db"))


@dataclass
class Stock:
    """股票配置"""

    code: str
    name: str
    market: str
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Stock":
        return cls(
            code=data["code"],
            name=data["name"],
            market=data["market"],
            notes=data.get("notes", ""),
        )


@dataclass
class ETF:
    """ETF配置"""

    code: str
    name: str

    @classmethod
    def from_dict(cls, data: dict) -> "ETF":
        return cls(code=data["code"], name=data["name"])


@dataclass
class Config:
    """应用配置"""

    # 基础配置
    logger: LoggerSettings
    strategy: StrategySettings
    trading_hours: TradingHours
    risk_control: RiskControlSettings
    signal_evaluation: SignalEvaluationConfig
    alert: AlertSettings
    data_sources: DataSourcesSettings
    database: DatabaseSettings

    # 股票和ETF列表
    my_stocks: list = None
    watch_etfs: list = None

    def __post_init__(self):
        if self.my_stocks is None:
            self.my_stocks = []
        if self.watch_etfs is None:
            self.watch_etfs = []

    @classmethod
    def load(cls, config_path: str = "config/settings.yaml", stocks_path: str = "config/stocks.yaml") -> "Config":
        """
        加载配置文件

        Args:
            config_path: 主配置文件路径
            stocks_path: 股票配置文件路径

        Returns:
            Config: 配置对象
        """
        config_file = Path(config_path)
        stocks_file = Path(stocks_path)

        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        # 加载主配置
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # 加载股票配置
        my_stocks = []
        watch_etfs = []
        if stocks_file.exists():
            with open(stocks_file, "r", encoding="utf-8") as f:
                stocks_data = yaml.safe_load(f)

            my_stocks = [Stock.from_dict(s) for s in stocks_data.get("my_stocks", [])]
            watch_etfs = [ETF.from_dict(e) for e in stocks_data.get("watch_etfs", [])]

        # 构建配置对象
        return cls(
            logger=LoggerSettings.from_dict(config_data.get("logging", {})),
            strategy=StrategySettings.from_dict(config_data.get("strategy", {})),
            trading_hours=TradingHours.from_dict(config_data.get("trading_hours", {})),
            risk_control=RiskControlSettings.from_dict(config_data.get("risk_control", {})),
            signal_evaluation=SignalEvaluationConfig.from_dict(config_data.get("signal_evaluation", {})),
            alert=AlertSettings.from_dict(config_data.get("notification", {})),
            data_sources=DataSourcesSettings.from_dict(config_data.get("data_sources", {})),
            database=DatabaseSettings.from_dict(config_data.get("database", {})),
            my_stocks=my_stocks,
            watch_etfs=watch_etfs,
        )


# 全局配置实例
_config: Optional[Config] = None


def get(config_path: str = "config/settings.yaml", stocks_path: str = "config/stocks.yaml") -> Config:
    """
    获取配置实例

    Args:
        config_path: 主配置文件路径
        stocks_path: 股票配置文件路径

    Returns:
        Config: 配置对象
    """
    global _config
    if _config is None:
        _config = Config.load(config_path, stocks_path)
        # 自动设置日志
        setup(_config.logger)
    return _config
