"""
Unit tests for Signal Sender Components

Tests the notification senders for trading signals.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from backend.signal.sender import (
    NotificationSender,
    LogSender,
    NullSender,
    LogSenderRegistered,
    NullSenderRegistered,
    create_sender_from_config,
)
from backend.arbitrage.models import TradingSignal
from backend.utils.plugin_registry import sender_registry


@pytest.mark.unit
class TestNotificationSender:
    """测试通知发送器基类"""

    def test_send_signal_raises_not_implemented(self):
        """测试基类send_signal抛出NotImplementedError"""
        sender = NotificationSender()
        signal = Mock(spec=TradingSignal)

        with pytest.raises(NotImplementedError):
            sender.send_signal(signal)


@pytest.mark.unit
class TestLogSender:
    """测试日志发送器"""

    @pytest.fixture
    def sender(self):
        return LogSender()

    @pytest.fixture
    def sample_signal(self):
        return TradingSignal(
            signal_id="TEST_001",
            timestamp="2024-01-01 10:00:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1800.0,
            limit_time="10:00:00",
            locked_amount=1000000,
            change_pct=0.10,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.05,
            etf_price=4.5,
            etf_premium=0.5,
            reason="测试信号",
            confidence="高",
            risk_level="中",
            actual_weight=0.05,
            weight_rank=1,
            top10_ratio=0.5
        )

    def test_send_signal_returns_true(self, sender, sample_signal):
        """测试send_signal返回True"""
        result = sender.send_signal(sample_signal)
        assert result is True

    @patch('backend.signal.sender.logger')
    def test_send_signal_logs_signal_info(self, mock_logger, sender, sample_signal):
        """测试send_signal记录信号信息"""
        sender.send_signal(sample_signal)

        # 验证调用了logger.info
        assert mock_logger.info.call_count == 5

        # 验证日志内容包含关键信息
        call_args_list = [str(call) for call in mock_logger.info.call_args_list]
        log_output = '\n'.join(call_args_list)

        assert "交易信号" in log_output or "600519" in log_output
        assert "贵州茅台" in log_output
        assert "510300" in log_output or "沪深300ETF" in log_output

    @patch('backend.signal.sender.logger')
    def test_send_signal_logs_price_info(self, mock_logger, sender, sample_signal):
        """测试send_signal记录价格信息"""
        sender.send_signal(sample_signal)

        call_args_list = [str(call) for call in mock_logger.info.call_args_list]
        log_output = '\n'.join(call_args_list)

        # 应该包含价格和涨幅信息
        assert "1800.00" in log_output or "1800" in log_output

    @patch('backend.signal.sender.logger')
    def test_send_signal_logs_weight_info(self, mock_logger, sender, sample_signal):
        """测试send_signal记录权重信息"""
        sender.send_signal(sample_signal)

        call_args_list = [str(call) for call in mock_logger.info.call_args_list]
        log_output = '\n'.join(call_args_list)

        # 应该包含权重和排名信息
        assert "5.00%" in log_output or "5%" in log_output
        assert "第1" in log_output or "1" in log_output

    @patch('backend.signal.sender.logger')
    def test_send_signal_logs_confidence_and_risk(self, mock_logger, sender, sample_signal):
        """测试send_signal记录置信度和风险"""
        sender.send_signal(sample_signal)

        call_args_list = [str(call) for call in mock_logger.info.call_args_list]
        log_output = '\n'.join(call_args_list)

        assert "高" in log_output  # 置信度
        assert "中" in log_output  # 风险等级

    @patch('backend.signal.sender.logger')
    def test_send_signal_logs_reason(self, mock_logger, sender, sample_signal):
        """测试send_signal记录原因说明"""
        sender.send_signal(sample_signal)

        call_args_list = [str(call) for call in mock_logger.info.call_args_list]
        log_output = '\n'.join(call_args_list)

        assert "测试信号" in log_output


@pytest.mark.unit
class TestNullSender:
    """测试空发送器"""

    @pytest.fixture
    def sender(self):
        return NullSender()

    @pytest.fixture
    def sample_signal(self):
        return Mock(spec=TradingSignal)

    def test_send_signal_returns_true(self, sender, sample_signal):
        """测试send_signal返回True"""
        result = sender.send_signal(sample_signal)
        assert result is True

    @patch('backend.signal.sender.logger')
    def test_send_signal_does_not_log(self, mock_logger, sender, sample_signal):
        """测试send_signal不记录日志"""
        sender.send_signal(sample_signal)
        mock_logger.info.assert_not_called()


@pytest.mark.unit
class TestRegisteredSenders:
    """测试注册的发送器"""

    def test_log_sender_is_registered(self):
        """测试日志发送器已注册"""
        assert "log" in sender_registry.list_names()

    def test_null_sender_is_registered(self):
        """测试空发送器已注册"""
        assert "null" in sender_registry.list_names()

    def test_log_sender_registered_instance(self):
        """测试注册的日志发送器类可用"""
        sender_class = sender_registry.get("log")
        # sender_registry.get() 返回的是类，不是实例
        assert sender_class in (LogSender, LogSenderRegistered, type(LogSender()))
        # 创建实例并验证
        sender = sender_class()
        assert isinstance(sender, NotificationSender)

    def test_null_sender_registered_instance(self):
        """测试注册的空发送器类可用"""
        sender_class = sender_registry.get("null")
        # sender_registry.get() 返回的是类，不是实例
        assert sender_class in (NullSender, NullSenderRegistered, type(NullSender()))
        # 创建实例并验证
        sender = sender_class()
        assert isinstance(sender, NotificationSender)

    def test_log_sender_registered_works(self):
        """测试注册的日志发送器可以工作"""
        sender_class = sender_registry.get("log")
        sender = sender_class()

        signal = TradingSignal(
            signal_id="TEST_001",
            timestamp="2024-01-01 10:00:00",
            stock_code="000001",
            stock_name="测试股票",
            stock_price=10.0,
            limit_time="10:00:00",
            locked_amount=1000000,
            change_pct=0.10,
            etf_code="510300",
            etf_name="测试ETF",
            etf_weight=0.05,
            etf_price=4.5,
            etf_premium=0.5,
            reason="测试",
            confidence="高",
            risk_level="中",
            actual_weight=0.05,
            weight_rank=1,
            top10_ratio=0.5
        )

        result = sender.send_signal(signal)
        assert result is True

    def test_null_sender_registered_works(self):
        """测试注册的空发送器可以工作"""
        sender_class = sender_registry.get("null")
        sender = sender_class()

        signal = Mock(spec=TradingSignal)
        result = sender.send_signal(signal)
        assert result is True


@pytest.mark.unit
class TestCreateSenderFromConfig:
    """测试从配置创建发送器"""

    @pytest.fixture
    def sample_signal(self):
        return TradingSignal(
            signal_id="TEST_001",
            timestamp="2024-01-01 10:00:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1800.0,
            limit_time="10:00:00",
            locked_amount=1000000,
            change_pct=0.10,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.05,
            etf_price=4.5,
            etf_premium=0.5,
            reason="测试信号",
            confidence="高",
            risk_level="中",
            actual_weight=0.05,
            weight_rank=1,
            top10_ratio=0.5
        )

    def test_returns_log_sender_when_no_alert_config(self, sample_signal):
        """测试无alert配置时返回日志发送器"""
        config = Mock()

        sender = create_sender_from_config(config)

        assert isinstance(sender, LogSender)
        result = sender.send_signal(sample_signal)
        assert result is True

    def test_returns_log_sender_when_alert_enabled_true(self, sample_signal):
        """测试alert.enabled=True时返回日志发送器"""
        config = Mock()
        config.alert.enabled = True

        sender = create_sender_from_config(config)

        assert isinstance(sender, LogSender)
        result = sender.send_signal(sample_signal)
        assert result is True

    def test_returns_null_sender_when_alert_enabled_false(self, sample_signal):
        """测试alert.enabled=False时返回空发送器"""
        config = Mock()
        config.alert.enabled = False

        sender = create_sender_from_config(config)

        assert isinstance(sender, NullSender)
        result = sender.send_signal(sample_signal)
        assert result is True

    @patch('backend.signal.sender.logger')
    def test_logs_info_when_alert_disabled(self, mock_logger, sample_signal):
        """测试禁用通知时记录日志"""
        config = Mock()
        config.alert.enabled = False

        sender = create_sender_from_config(config)

        mock_logger.info.assert_called_once()
        assert "通知已禁用" in str(mock_logger.info.call_args)

    def test_handles_missing_alert_attribute_gracefully(self, sample_signal):
        """测试缺少alert属性时使用默认"""
        config = Mock(spec=['trading', 'strategy'])  # 没有alert属性

        sender = create_sender_from_config(config)

        # 应该返回默认的LogSender
        assert isinstance(sender, LogSender)

    def test_handles_missing_enabled_attribute_gracefully(self, sample_signal):
        """测试alert缺少enabled属性时使用默认"""
        config = Mock()
        config.alert = Mock(spec=['email', 'dingtalk'])  # 没有enabled属性

        sender = create_sender_from_config(config)

        # 应该返回默认的LogSender
        assert isinstance(sender, LogSender)


@pytest.mark.unit
class TestSenderInheritance:
    """测试发送器继承关系"""

    def test_log_sender_is_notification_sender(self):
        """测试LogSender是NotificationSender的子类"""
        assert issubclass(LogSender, NotificationSender)

    def test_null_sender_is_notification_sender(self):
        """测试NullSender是NotificationSender的子类"""
        assert issubclass(NullSender, NotificationSender)

    def test_registered_log_sender_inherits_log_sender(self):
        """测试注册的LogSender继承自LogSender"""
        assert issubclass(LogSenderRegistered, LogSender)

    def test_registered_null_sender_inherits_null_sender(self):
        """测试注册的NullSender继承自NullSender"""
        assert issubclass(NullSenderRegistered, NullSender)
