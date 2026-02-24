"""
Unit tests for Signal Repository

Tests the InMemorySignalRepository implementation.
"""

import pytest
import os
import tempfile
import json
from pathlib import Path

from backend.signal.memory_repository import InMemorySignalRepository
from backend.signal.db_repository import DBSignalRepository
from backend.arbitrage.models import TradingSignal
from backend.utils.clock import FrozenClock, reset_clock, set_clock, CHINA_TZ
from datetime import datetime


@pytest.mark.unit
class TestInMemorySignalRepository:
    """测试InMemorySignalRepository - 内存仓储"""

    def setup_method(self):
        """每个测试前创建仓储"""
        self.repository = InMemorySignalRepository()

    def test_save_signal(self):
        """测试保存信号"""
        signal = TradingSignal(
            signal_id="test_signal_001",
            timestamp="2024-01-15 14:30:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1680.0,
            change_pct=10.0,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.08,
            etf_price=4.5,
            etf_premium=0.5,
            reason="涨停套利",
            confidence="高",
            risk_level="中",
            actual_weight=0.08,
            weight_rank=1,
            top10_ratio=0.25
        )

        result = self.repository.save(signal)
        assert result is True

    def test_save_multiple_signals(self):
        """测试保存多个信号"""
        signal1 = TradingSignal(
            signal_id="test_signal_001",
            timestamp="2024-01-15 14:30:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1680.0,
            change_pct=10.0,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.08,
            etf_price=4.5,
            etf_premium=0.5,
            reason="涨停套利",
            confidence="高",
            risk_level="中",
            actual_weight=0.08,
            weight_rank=1,
            top10_ratio=0.25
        )

        signal2 = TradingSignal(
            signal_id="test_signal_002",
            timestamp="2024-01-15 14:30:00",
            stock_code="300750",
            stock_name="宁德时代",
            stock_price=180.0,
            change_pct=10.0,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.06,
            etf_price=4.5,
            etf_premium=0.5,
            reason="涨停套利",
            confidence="中",
            risk_level="中",
            actual_weight=0.06,
            weight_rank=2,
            top10_ratio=0.25
        )

        self.repository.save_all([signal1, signal2])
        assert self.repository.get_count() == 2

    def test_get_all_signals(self):
        """测试获取所有信号"""
        signal = TradingSignal(
            signal_id="test_signal_001",
            timestamp="2024-01-15 14:30:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1680.0,
            change_pct=10.0,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.08,
            etf_price=4.5,
            etf_premium=0.5,
            reason="涨停套利",
            confidence="高",
            risk_level="中",
            actual_weight=0.08,
            weight_rank=1,
            top10_ratio=0.25
        )

        self.repository.save(signal)
        signals = self.repository.get_all_signals()

        assert len(signals) == 1
        assert signals[0].stock_code == "600519"

    def test_get_signal_by_id(self):
        """测试根据ID获取信号"""
        signal = TradingSignal(
            signal_id="test_signal_001",
            timestamp="2024-01-15 14:30:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1680.0,
            change_pct=10.0,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.08,
            etf_price=4.5,
            etf_premium=0.5,
            reason="涨停套利",
            confidence="高",
            risk_level="中",
            actual_weight=0.08,
            weight_rank=1,
            top10_ratio=0.25
        )

        self.repository.save(signal)
        retrieved = self.repository.get_signal("test_signal_001")

        assert retrieved is not None
        assert retrieved.stock_code == "600519"

    def test_clear_signals(self):
        """测试清空信号"""
        signal = TradingSignal(
            signal_id="test_signal_001",
            timestamp="2024-01-15 14:30:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1680.0,
            change_pct=10.0,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.08,
            etf_price=4.5,
            etf_premium=0.5,
            reason="涨停套利",
            confidence="高",
            risk_level="中",
            actual_weight=0.08,
            weight_rank=1,
            top10_ratio=0.25
        )

        self.repository.save(signal)
        assert self.repository.get_count() == 1

        self.repository.clear()
        assert self.repository.get_count() == 0

    def test_get_today_signals(self):
        """测试获取今天的信号"""
        # 设置固定时间
        frozen_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=CHINA_TZ)
        set_clock(FrozenClock(frozen_time))

        signal = TradingSignal(
            signal_id="test_signal_001",
            timestamp="2024-01-15 14:30:00",
            stock_code="600519",
            stock_name="贵州茅台",
            stock_price=1680.0,
            change_pct=10.0,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.08,
            etf_price=4.5,
            etf_premium=0.5,
            reason="涨停套利",
            confidence="高",
            risk_level="中",
            actual_weight=0.08,
            weight_rank=1,
            top10_ratio=0.25
        )

        self.repository.save(signal)
        today_signals = self.repository.get_today_signals()

        assert len(today_signals) == 1

        # 清理
        reset_clock()

    def test_get_recent_signals(self):
        """测试获取最近的信号"""
        # 保存多个信号
        for i in range(5):
            signal = TradingSignal(
                signal_id=f"test_signal_{i}",
                timestamp=f"2024-01-15 14:{30+i}:00",
                stock_code=f"60051{i}",
                stock_name=f"股票{i}",
                stock_price=10.0 + i,
                change_pct=10.0,
                etf_code="510300",
                etf_name="沪深300ETF",
                etf_weight=0.08,
                etf_price=4.5,
                etf_premium=0.5,
                reason="涨停套利",
                confidence="高",
                risk_level="中",
                actual_weight=0.08,
                weight_rank=1,
                top10_ratio=0.25
            )
            self.repository.save(signal)

        recent = self.repository.get_recent_signals(limit=3)
        assert len(recent) == 3

    def test_thread_safety(self):
        """测试线程安全"""
        import threading

        def save_signals(count):
            for i in range(count):
                signal = TradingSignal(
                    signal_id=f"test_signal_{i}",
                    timestamp="2024-01-15 14:30:00",
                    stock_code=f"60051{i}",
                    stock_name=f"股票{i}",
                    stock_price=10.0 + i,
                    change_pct=10.0,
                    etf_code="510300",
                    etf_name="沪深300ETF",
                    etf_weight=0.08,
                    etf_price=4.5,
                    etf_premium=0.5,
                    reason="涨停套利",
                    confidence="高",
                    risk_level="中",
                    actual_weight=0.08,
                    weight_rank=1,
                    top10_ratio=0.25
                )
                self.repository.save(signal)

        # 创建多个线程
        threads = []
        for _ in range(3):
            t = threading.Thread(target=save_signals, args=(10,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 验证所有信号都已保存
        assert self.repository.get_count() == 30
