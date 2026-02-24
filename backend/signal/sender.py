"""
消息通知模块

提供通知接口定义，默认输出信号到日志。
用户可以通过插件注册表自定义通知方式。

Example:
    @sender_registry.register("my_channel", description="我的通知渠道")
    class MySender(NotificationSender):
        def send_signal(self, signal):
            # 实现通知逻辑
            pass
"""

from loguru import logger

from backend.arbitrage.models import TradingSignal
from backend.utils.plugin_registry import sender_registry


class NotificationSender:
    """
    消息通知发送器基类

    所有自定义通知渠道应继承此类并使用 @sender_registry.register() 装饰器注册。
    """

    def send_signal(self, signal: TradingSignal) -> bool:
        """
        发送信号通知

        Args:
            signal: 交易信号

        Returns:
            是否发送成功
        """
        raise NotImplementedError


@sender_registry.register(
    "log",
    priority=0,
    description="日志输出（默认）",
    version="1.0.0"
)
class LogSender(NotificationSender):
    """
    日志输出发送器（默认）

    将信号输出到日志系统，用于调试和记录。
    """

    def send_signal(self, signal: TradingSignal) -> bool:
        """
        将信号输出到日志

        Args:
            signal: 交易信号

        Returns:
            始终返回 True
        """
        logger.info(
            f"📈 交易信号: {signal.stock_name}({signal.stock_code}) "
            f"-> {signal.etf_name}({signal.etf_code})"
        )
        logger.info(f"   价格: ¥{signal.stock_price:.2f}, 涨幅: +{signal.change_pct:.2f}%")
        logger.info(f"   权重: {signal.etf_weight*100:.2f}%, 排名: 第{signal.weight_rank}")
        logger.info(f"   置信度: {signal.confidence}, 风险: {signal.risk_level}")
        logger.info(f"   说明: {signal.reason}")
        return True


@sender_registry.register(
    "null",
    priority=0,
    description="空发送器（禁用通知）",
    version="1.0.0"
)
class NullSender(NotificationSender):
    """
    空发送器（不发送通知）

    用于测试或完全禁用通知时。
    """

    def send_signal(self, signal: TradingSignal) -> bool:
        """不发送任何通知，返回成功"""
        return True


def create_sender_from_config(config) -> NotificationSender:
    """
    根据配置创建发送器

    当前实现：返回日志发送器
    用户可以通过插件注册表自定义其他通知方式

    Args:
        config: 应用配置

    Returns:
        发送器实例
    """
    # 检查是否禁用通知
    if hasattr(config, 'alert') and hasattr(config.alert, 'enabled'):
        if not config.alert.enabled:
            logger.info("通知已禁用，使用空发送器")
            return NullSender()

    # 默认使用日志发送器
    return LogSender()
