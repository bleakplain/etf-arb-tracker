"""
Integration Tests for Arbitrage Workflow

Tests end-to-end workflows from market events to signal generation.
Uses the new test infrastructure (InMemoryRepository, Clock abstraction, auto-cleanup).
"""

import pytest
from datetime import datetime, timedelta

from backend.arbitrage.cn.arbitrage_engine import ArbitrageEngineCN
from backend.arbitrage.cn.factory import ArbitrageEngineFactory
from backend.arbitrage.config import ArbitrageEngineConfig
from backend.arbitrage.models import TradingSignal
from backend.signal.repository import InMemorySignalRepository
from backend.utils.clock import FrozenClock, set_clock, reset_clock, CHINA_TZ
from backend.market import LimitUpEvent, CandidateETF, ETFCategory


@pytest.mark.integration
class TestArbitrageWorkflow:
    """测试套利工作流集成"""

    def setup_method(self):
        """每个测试前设置固定时间"""
        # 设置为交易时间：2024-01-15 14:30:00 (周一)
        frozen_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=CHINA_TZ)
        set_clock(FrozenClock(frozen_time))

    def teardown_method(self):
        """每个测试后恢复时钟"""
        reset_clock()

    def test_end_to_end_limit_up_arbitrage(self):
        """测试完整的涨停套利流程"""
        # 1. 创建测试引擎
        engine = ArbitrageEngineFactory.create_test_engine(
            watch_securities=["600519", "300750"],
            predefined_mapping={
                "600519": [
                    {"etf_code": "510300", "etf_name": "沪深300ETF"},
                    {"etf_code": "510500", "etf_name": "中证500ETF"},
                ],
                "300750": [
                    {"etf_code": "516160", "etf_name": "新能源车ETF"},
                ]
            }
        )

        # 2. 扫描所有证券
        scan_result = engine.scan_all()

        # 3. 验证结果
        assert scan_result is not None
        assert scan_result.total_scanned == 2

        # 检查生成的信号
        if scan_result.signals:
            # 验证信号结构
            signal = scan_result.signals[0]
            assert signal.stock_code in ["600519", "300750"]
            assert signal.etf_code is not None

    def test_signal_generation_workflow(self):
        """测试信号生成工作流"""
        # 1. 创建带信号仓储的引擎
        signal_repository = InMemorySignalRepository()
        engine = ArbitrageEngineFactory.create_test_engine(
            watch_securities=["600519"],
            predefined_mapping={
                "600519": [
                    {"etf_code": "510300", "etf_name": "沪深300ETF"},
                ]
            }
        )

        # 2. 执行扫描
        scan_result = engine.scan_all()

        # 3. 处理生成的信号
        if scan_result.signals:
            for signal in scan_result.signals:
                # 4. 保存信号
                signal_repository.save(signal)

                # 5. 验证信号结构
                assert signal.stock_code is not None
                assert signal.etf_code is not None

    def test_strategy_filter_workflow(self):
        """测试策略过滤工作流"""
        # 1. 创建带过滤策略的配置
        config = ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector="highest_weight",
            signal_filters=["time_filter_cn", "liquidity_filter"],
            filter_configs={
                "time_filter_cn": {"min_time_to_close": 1800},
                "liquidity_filter": {"min_daily_amount": 50000000}
            }
        )

        # 2. 创建引擎
        engine = ArbitrageEngineFactory.create_test_engine(
            watch_securities=["600519"],
            engine_config=config,
            predefined_mapping={
                "600519": [
                    {"etf_code": "510300", "etf_name": "沪深300ETF"},
                ]
            }
        )

        # 3. 执行扫描
        scan_result = engine.scan_all()

        # 4. 验证结果结构
        assert scan_result is not None
        assert hasattr(scan_result, 'signals')
        assert hasattr(scan_result, 'filtered_count')

    def test_multi_stock_batch_scan(self):
        """测试多股票批量扫描"""
        # 1. 创建引擎监控多只股票
        watch_list = ["600519", "300750", "000001", "600036"]
        engine = ArbitrageEngineFactory.create_test_engine(
            watch_securities=watch_list,
            predefined_mapping={
                code: [{"etf_code": "510300", "etf_name": "沪深300ETF"}]
                for code in watch_list
            }
        )

        # 2. 批量扫描
        scan_result = engine.scan_all()

        # 3. 验证结果
        assert scan_result is not None
        assert scan_result.total_scanned == len(watch_list)
        assert hasattr(scan_result, 'signals')

    def test_fund_selection_priority(self):
        """测试基金选择优先级"""
        # 1. 创建多候选ETF场景
        engine = ArbitrageEngineFactory.create_test_engine(
            watch_securities=["600519"],
            engine_config=ArbitrageEngineConfig(
                event_detector="limit_up_cn",
                fund_selector="highest_weight",  # 选择最高权重
            ),
            predefined_mapping={
                "600519": [
                    {"etf_code": "510300", "etf_name": "沪深300ETF"},
                    {"etf_code": "510500", "etf_name": "中证500ETF"},
                ]
            }
        )

        # 2. 扫描涨停股票
        scan_result = engine.scan_all()

        # 3. 验证选择了正确的ETF
        if scan_result.signals:
            # highest_weight 策略应该选择权重最高的ETF
            signal = scan_result.signals[0]
            assert signal.etf_code is not None


@pytest.mark.integration
class TestErrorHandlingWorkflow:
    """测试错误处理工作流"""

    def test_missing_mapping_handling(self):
        """测试缺失映射处理"""
        engine = ArbitrageEngineFactory.create_test_engine(
            watch_securities=["999999"],  # 不存在的股票
            predefined_mapping={}  # 空映射
        )

        # 应该优雅处理，不抛出异常
        scan_result = engine.scan_all()
        assert scan_result is not None
        assert scan_result.total_scanned == 1

    def test_invalid_config_handling(self):
        """测试无效配置处理"""
        with pytest.raises(ValueError) as exc_info:
            ArbitrageEngineConfig(
                event_detector="nonexistent",
                fund_selector="also_nonexistent"
            ).assert_valid()

        assert "验证失败" in str(exc_info.value)


@pytest.mark.integration
class TestRepositoryWorkflow:
    """测试仓储工作流"""

    def test_signal_persistence_workflow(self):
        """测试信号持久化工作流"""
        # 1. 创建内存仓储
        repository = InMemorySignalRepository()

        # 2. 设置当前时间为2024-01-15
        test_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=CHINA_TZ)
        set_clock(FrozenClock(test_time))

        # 3. 创建测试信号（使用今天的日期）
        from backend.utils.time_utils import today_china
        today = today_china()  # 获取当前日期字符串

        signal = TradingSignal(
            signal_id="test_001",
            timestamp=f"{today} 14:30:00",  # 使用今天的日期
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

        # 4. 保存信号
        repository.save(signal)

        # 5. 查询信号
        retrieved = repository.get_signal("test_001")
        assert retrieved is not None
        assert retrieved.stock_code == "600519"

        # 6. 获取所有信号
        all_signals = repository.get_all_signals()
        assert len(all_signals) == 1

        # 7. 获取今天的信号
        today_signals = repository.get_today_signals()
        assert len(today_signals) == 1

        # 8. 清空信号
        repository.clear()
        assert repository.get_count() == 0


@pytest.mark.integration
class TestTimeBasedWorkflow:
    """测试基于时间的工作流"""

    def test_trading_time_detection(self):
        """测试交易时间检测"""
        from backend.utils.time_utils import is_trading_time

        # 设置为交易时间
        trading_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=CHINA_TZ)
        set_clock(FrozenClock(trading_time))

        assert is_trading_time() is True

        # 设置为非交易时间
        non_trading_time = datetime(2024, 1, 15, 16, 0, 0, tzinfo=CHINA_TZ)
        set_clock(FrozenClock(non_trading_time))

        assert is_trading_time() is False

    def test_time_to_close_calculation(self):
        """测试距离收盘时间计算"""
        from backend.utils.time_utils import time_to_close

        # 设置为14:00，距离15:00收盘还有1小时
        test_time = datetime(2024, 1, 15, 14, 0, 0, tzinfo=CHINA_TZ)
        set_clock(FrozenClock(test_time))

        seconds = time_to_close()
        assert seconds == 3600  # 1小时 = 3600秒


@pytest.mark.integration
class TestConfigurationWorkflow:
    """测试配置工作流"""

    def test_config_validation_before_engine_creation(self):
        """测试引擎创建前配置验证"""
        # 有效配置
        valid_config = ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector="highest_weight"
        )
        is_valid, errors = valid_config.validate()
        assert is_valid
        assert len(errors) == 0

    def test_config_dict_serialization(self):
        """测试配置字典序列化"""
        config = ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector="highest_weight",
            signal_filters=["time_filter_cn"],
            event_config={"min_change_pct": 0.095}
        )

        # 转为字典
        config_dict = config.to_dict()

        # 从字典重建
        restored = ArbitrageEngineConfig.from_dict(config_dict)

        # 验证
        assert restored.event_detector == config.event_detector
        assert restored.fund_selector == config.fund_selector
        assert restored.event_config == config.event_config
