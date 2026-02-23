"""
Unit tests for Configuration Validation

Tests the configuration validation mechanism for ArbitrageEngineConfig.
"""

import pytest
from backend.arbitrage.config import ArbitrageEngineConfig
from backend.arbitrage.cn.strategies.event_detectors import LimitUpDetectorCN
from backend.arbitrage.cn.strategies.fund_selectors import HighestWeightSelector
from backend.arbitrage.cn.strategies.signal_filters import TimeFilterCN, LiquidityFilter


@pytest.mark.unit
class TestArbitrageEngineConfigValidation:
    """测试ArbitrageEngineConfig配置验证"""

    def test_valid_config_passes_validation(self):
        """测试有效配置通过验证"""
        config = ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector="highest_weight",
            signal_filters=["time_filter_cn", "liquidity_filter"]
        )

        is_valid, errors = config.validate()
        assert is_valid
        assert len(errors) == 0

    def test_empty_event_detector_fails(self):
        """测试空事件检测器失败"""
        config = ArbitrageEngineConfig(
            event_detector="",  # 空
            fund_selector="highest_weight"
        )

        is_valid, errors = config.validate()
        assert not is_valid
        assert any("event_detector" in e for e in errors)

    def test_empty_fund_selector_fails(self):
        """测试空基金选择器失败"""
        config = ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector=""  # 空
        )

        is_valid, errors = config.validate()
        assert not is_valid
        assert any("fund_selector" in e for e in errors)

    def test_unknown_event_detector_fails(self):
        """测试未知事件检测器失败"""
        config = ArbitrageEngineConfig(
            event_detector="unknown_detector",  # 不存在
            fund_selector="highest_weight"
        )

        is_valid, errors = config.validate()
        assert not is_valid
        assert any("unknown_detector" in e and "未注册" in e for e in errors)

    def test_unknown_fund_selector_fails(self):
        """测试未知基金选择器失败"""
        config = ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector="unknown_selector"  # 不存在
        )

        is_valid, errors = config.validate()
        assert not is_valid
        assert any("unknown_selector" in e and "未注册" in e for e in errors)

    def test_unknown_filter_fails(self):
        """测试未知过滤器失败"""
        config = ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector="highest_weight",
            signal_filters=["unknown_filter"]  # 不存在
        )

        is_valid, errors = config.validate()
        assert not is_valid
        assert any("unknown_filter" in e and "未注册" in e for e in errors)

    def test_validation_shows_available_strategies(self):
        """测试验证显示可用策略"""
        config = ArbitrageEngineConfig(
            event_detector="wrong_name",
            fund_selector="wrong_selector"
        )

        is_valid, errors = config.validate()
        assert not is_valid

        # 检查错误消息包含可用策略列表
        error_text = "; ".join(errors)
        assert "limit_up_cn" in error_text  # 可用的事件检测器
        assert "highest_weight" in error_text  # 可用的基金选择器

    def test_assert_valid_raises_on_invalid_config(self):
        """测试assert_valid在无效配置时抛出异常"""
        config = ArbitrageEngineConfig(
            event_detector="",  # 无效
            fund_selector=""
        )

        with pytest.raises(ValueError) as exc_info:
            config.assert_valid()

        assert "验证失败" in str(exc_info.value)

    def test_assert_valid_does_not_raise_on_valid_config(self):
        """测试assert_valid在有效配置时不抛出异常"""
        config = ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector="highest_weight"
        )

        # 不应该抛出异常
        config.assert_valid()

    def test_from_dict_creates_valid_config(self):
        """测试from_dict创建有效配置"""
        data = {
            "event_detector": "limit_up_cn",
            "fund_selector": "highest_weight",
            "signal_filters": ["time_filter_cn"]
        }

        config = ArbitrageEngineConfig.from_dict(data)
        assert config.event_detector == "limit_up_cn"
        assert config.fund_selector == "highest_weight"
        assert "time_filter_cn" in config.signal_filters

    def test_to_dict_and_from_dict_roundtrip(self):
        """测试to_dict和from_dict往返转换"""
        original = ArbitrageEngineConfig(
            event_detector="limit_up_cn",
            fund_selector="highest_weight",
            signal_filters=["time_filter_cn", "liquidity_filter"],
            event_config={"min_change_pct": 0.095},
            fund_config={"min_weight": 0.05}
        )

        # 转为字典
        data = original.to_dict()

        # 从字典重建
        restored = ArbitrageEngineConfig.from_dict(data)

        # 验证
        assert restored.event_detector == original.event_detector
        assert restored.fund_selector == original.fund_selector
        assert restored.signal_filters == original.signal_filters
        assert restored.event_config == original.event_config
        assert restored.fund_config == original.fund_config


@pytest.mark.unit
class TestStrategyFromConfig:
    """测试策略的from_config工厂方法"""

    def test_event_detector_from_config(self):
        """测试事件检测器from_config"""
        config = {"min_change_pct": 0.095}
        detector = LimitUpDetectorCN.from_config(config)

        assert detector is not None
        assert detector.strategy_name == "limit_up_cn"

    def test_event_detector_from_empty_config(self):
        """测试事件检测器from_config空配置"""
        detector = LimitUpDetectorCN.from_config(None)

        assert detector is not None
        assert detector.strategy_name == "limit_up_cn"

    def test_fund_selector_from_config(self):
        """测试基金选择器from_config"""
        config = {"min_weight": 0.05}
        selector = HighestWeightSelector.from_config(config)

        assert selector is not None
        assert selector.strategy_name == "highest_weight"

    def test_signal_filter_from_config(self):
        """测试信号过滤器from_config"""
        config = {"min_time_to_close": 1800}
        filter_strategy = TimeFilterCN.from_config(config)

        assert filter_strategy is not None
        assert filter_strategy.strategy_name == "time_filter_cn"

    def test_liquidity_filter_from_config(self):
        """测试流动性过滤器from_config"""
        config = {"min_daily_amount": 50000000}
        filter_strategy = LiquidityFilter.from_config(config)

        assert filter_strategy is not None
        assert filter_strategy.strategy_name == "liquidity_filter"
