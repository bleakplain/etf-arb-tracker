"""
单元测试 - SignalManager
"""

import pytest
from unittest.mock import Mock, MagicMock
from backend.signal.manager import SignalManager
from backend.arbitrage.models import TradingSignal


class TestSignalManager:
    """信号管理器测试"""

    def test_init_with_repository_only(self):
        """测试只传入仓储的初始化"""
        mock_repo = Mock()
        manager = SignalManager(repository=mock_repo)

        assert manager._repository == mock_repo
        assert manager._sender is None

    def test_init_with_repository_and_sender(self):
        """测试传入仓储和发送器的初始化"""
        mock_repo = Mock()
        mock_sender = Mock()
        manager = SignalManager(repository=mock_repo, sender=mock_sender)

        assert manager._repository == mock_repo
        assert manager._sender == mock_sender

    def test_save_and_notify_success_without_sender(self):
        """测试保存信号成功（无发送器）"""
        mock_repo = Mock()
        mock_repo.save.return_value = True

        signal = TradingSignal(
            signal_id="TEST_001",
            timestamp="2024-01-01 10:00:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1800.0,
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

        manager = SignalManager(repository=mock_repo)
        result = manager.save_and_notify(signal)

        assert result is True
        mock_repo.save.assert_called_once_with(signal)

    def test_save_and_notify_success_with_sender(self):
        """测试保存和发送信号成功"""
        mock_repo = Mock()
        mock_repo.save.return_value = True
        mock_sender = Mock()
        mock_sender.send_signal.return_value = True

        signal = TradingSignal(
            signal_id="TEST_002",
            timestamp="2024-01-01 10:00:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1800.0,
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

        manager = SignalManager(repository=mock_repo, sender=mock_sender)
        result = manager.save_and_notify(signal)

        assert result is True
        mock_repo.save.assert_called_once_with(signal)
        mock_sender.send_signal.assert_called_once_with(signal)

    def test_save_and_notify_repository_failure(self):
        """测试仓储保存失败"""
        mock_repo = Mock()
        mock_repo.save.side_effect = Exception("保存失败")

        signal = TradingSignal(
            signal_id="TEST_003",
            timestamp="2024-01-01 10:00:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1800.0,
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

        manager = SignalManager(repository=mock_repo)
        result = manager.save_and_notify(signal)

        assert result is False

    def test_get_all_signals(self):
        """测试获取所有信号"""
        mock_repo = Mock()
        expected_signals = [Mock(), Mock()]
        mock_repo.get_all_signals.return_value = expected_signals

        manager = SignalManager(repository=mock_repo)
        result = manager.get_all_signals()

        assert result == expected_signals
        mock_repo.get_all_signals.assert_called_once()

    def test_get_signal(self):
        """测试获取单个信号"""
        mock_repo = Mock()
        expected_signal = Mock()
        mock_repo.get_signal.return_value = expected_signal

        manager = SignalManager(repository=mock_repo)
        result = manager.get_signal("TEST_001")

        assert result == expected_signal
        mock_repo.get_signal.assert_called_once_with("TEST_001")

    def test_get_signal_not_found(self):
        """测试获取不存在的信号"""
        mock_repo = Mock()
        mock_repo.get_signal.return_value = None

        manager = SignalManager(repository=mock_repo)
        result = manager.get_signal("NONEXISTENT")

        assert result is None
        mock_repo.get_signal.assert_called_once_with("NONEXISTENT")
