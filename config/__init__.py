"""
配置模块

统一加载和管理所有配置项
"""

import yaml
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from config.logger import LoggerSettings, setup
from config.strategy import StrategySettings, TradingHours, RiskControlSettings, SignalEvaluationConfig
from config.alert import AlertSettings


def _expand_env_vars(value):
    """
    递归展开配置值中的环境变量

    支持格式：${VAR_NAME} 或 ${VAR_NAME:default_value}

    Args:
        value: 配置值（可能是字符串、列表、字典）

    Returns:
        展开环境变量后的值
    """
    if isinstance(value, str):
        # 匹配 ${VAR_NAME} 或 ${VAR_NAME:default}
        pattern = r'\$\{([^:}]+)(?::([^}]*))?\}'

        def replace_env_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ''
            return os.environ.get(var_name, default_value)

        return re.sub(pattern, replace_env_var, value)

    elif isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [_expand_env_vars(item) for item in value]

    return value


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
class ETFCategories:
    """ETF分类配置"""

    broad_index: list = None
    tech: list = None
    consumer: list = None
    financial: list = None

    def __post_init__(self):
        if self.broad_index is None:
            self.broad_index = []
        if self.tech is None:
            self.tech = []
        if self.consumer is None:
            self.consumer = []
        if self.financial is None:
            self.financial = []

    @classmethod
    def from_dict(cls, data: dict) -> "ETFCategories":
        return cls(
            broad_index=data.get("broad_index", []),
            tech=data.get("tech", []),
            consumer=data.get("consumer", []),
            financial=data.get("financial", []),
        )

    def get_category(self, etf_code: str) -> str:
        """根据ETF代码获取分类"""
        etf_code = etf_code.strip()
        if etf_code in self.broad_index:
            return "broad_index"
        elif etf_code in self.tech:
            return "tech"
        elif etf_code in self.consumer:
            return "consumer"
        elif etf_code in self.financial:
            return "financial"
        else:
            return "other"


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
    etf_categories: ETFCategories

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

        # 展开环境变量
        config_data = _expand_env_vars(config_data)

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
            etf_categories=ETFCategories.from_dict(config_data.get("etf_categories", {})),
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
