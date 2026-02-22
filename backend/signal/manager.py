"""信号管理服务 - 整合存储和通知"""

from typing import List, Optional
from loguru import logger

from backend.arbitrage.models import TradingSignal
from backend.signal.interfaces import ISignalRepository, ISignalSender


class SignalManager:
    """信号管理服务

    职责：
    1. 保存信号到仓储
    2. 发送信号通知
    3. 查询历史信号
    """

    def __init__(
        self,
        repository: ISignalRepository,
        sender: Optional[ISignalSender] = None
    ):
        """
        初始化信号管理器

        Args:
            repository: 信号仓储
            sender: 信号发送器（可选）
        """
        self._repository = repository
        self._sender = sender

    def save_and_notify(self, signal: TradingSignal) -> bool:
        """
        保存信号并发送通知

        Args:
            signal: 交易信号

        Returns:
            是否成功
        """
        try:
            # 保存信号
            self._repository.save(signal)
            logger.info(f"信号已保存: {signal.signal_id}")

            # 发送通知
            if self._sender:
                self._sender.send_signal(signal)
                logger.info(f"信号已发送: {signal.signal_id}")

            return True

        except Exception as e:
            logger.error(f"保存或发送信号失败: {e}")
            return False

    def get_all_signals(self) -> List[TradingSignal]:
        """获取所有信号"""
        return self._repository.get_all_signals()

    def get_signal(self, signal_id: str) -> Optional[TradingSignal]:
        """获取单个信号"""
        return self._repository.get_signal(signal_id)
