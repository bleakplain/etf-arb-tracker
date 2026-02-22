"""美股回测引擎（框架）"""

from typing import List, Optional, Callable
from datetime import datetime
from loguru import logger

from ..config import BacktestConfig


class USBacktestEngine:
    """美股回测引擎（框架）"""

    def __init__(
        self,
        config: BacktestConfig,
        progress_callback: Optional[Callable[[float], None]] = None
    ):
        """初始化美股回测引擎"""
        raise NotImplementedError("美股回测待实现")

    def initialize(self) -> None:
        """初始化回测环境"""
        raise NotImplementedError("美股回测待实现")

    def run(self):
        """运行回测"""
        raise NotImplementedError("美股回测待实现")
