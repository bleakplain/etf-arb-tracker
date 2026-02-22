"""
Unit tests for SignalEvaluator

Tests the signal evaluation module with mocked dependencies.
"""

import pytest
from unittest.mock import patch
from datetime import datetime

from backend.signal.evaluator import (
    SignalEvaluator,
    DefaultSignalEvaluator,
    ConservativeEvaluator,
    AggressiveEvaluator,
)
from config.strategy import SignalEvaluationConfig
from tests.fixtures.mocks import create_mock_limit_up_event, create_candidate_etf


@pytest.mark.unit
class TestSignalEvaluatorBase:
    """测试SignalEvaluator基类"""

    def test_get_time_to_close_returns_int(self):
        """测试_get_time_to_close返回整数值"""
        config = SignalEvaluationConfig()
        # 使用DefaultSignalEvaluator而不是抽象基类
        evaluator = DefaultSignalEvaluator(config)

        time_to_close = evaluator._get_time_to_close()
        assert isinstance(time_to_close, int)

    def test_get_time_to_close_negative_outside_trading_hours(self, fixed_datetime):
        """测试非交易时间返回负数"""
        # 设置为非交易时间
        with patch('backend.signal.evaluator.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 15, 16, 0, 0)  # 16:00

            config = SignalEvaluationConfig()
            evaluator = DefaultSignalEvaluator(config)

            time_to_close = evaluator._get_time_to_close()
            assert time_to_close == -1


@pytest.mark.unit
class TestDefaultSignalEvaluator:
    """测试DefaultSignalEvaluator"""

    @pytest.fixture
    def evaluator(self):
        """创建评估器实例"""
        config = SignalEvaluationConfig()
        return DefaultSignalEvaluator(config)

    @pytest.fixture
    def limit_up_event(self):
        """创建涨停事件"""
        return create_mock_limit_up_event('600519', '贵州茅台')

    def test_evaluate_returns_tuple(self, evaluator, limit_up_event):
        """测试evaluate返回元组"""
        etf_holding = create_candidate_etf('510300', weight=0.08, rank=1)

        result = evaluator.evaluate(limit_up_event, etf_holding)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] in ['高', '中', '低']  # 置信度
        assert result[1] in ['高', '中', '低']  # 风险等级

    def test_evaluate_high_weight_gives_high_confidence(self, evaluator, limit_up_event):
        """测试高权重产生高置信度"""
        etf_holding = create_candidate_etf('510300', weight=0.15, rank=5)

        confidence, risk = evaluator.evaluate(limit_up_event, etf_holding)

        assert confidence == '高'

    def test_evaluate_low_weight_gives_low_confidence(self, evaluator, limit_up_event):
        """测试低权重产生低置信度"""
        etf_holding = create_candidate_etf('510300', weight=0.02, rank=10)

        confidence, risk = evaluator.evaluate(limit_up_event, etf_holding)

        assert confidence == '低'

    def test_evaluate_high_rank_gives_high_confidence(self, evaluator, limit_up_event):
        """测试高排名（数值小）产生高置信度"""
        etf_holding = create_candidate_etf('510300', weight=0.04, rank=1)

        confidence, risk = evaluator.evaluate(limit_up_event, etf_holding)

        assert confidence == '高'


@pytest.mark.unit
class TestConservativeEvaluator:
    """测试ConservativeEvaluator"""

    @pytest.fixture
    def evaluator(self):
        """创建保守型评估器"""
        config = SignalEvaluationConfig()
        return ConservativeEvaluator(config)

    @pytest.fixture
    def limit_up_event(self):
        """创建涨停事件"""
        return create_mock_limit_up_event('600519', '贵州茅台')

    def test_conservative_stricter_requirements(self, evaluator, limit_up_event):
        """测试保守型评估器要求更严格"""
        # 0.08权重在默认评估器应该是中等置信度
        # 但在保守型评估器可能仍然不是高置信度
        etf_holding = create_candidate_etf('510300', weight=0.08, rank=3)

        confidence, risk = evaluator.evaluate(limit_up_event, etf_holding)

        # 保守型评估器需要>=0.15权重才给高置信度
        assert confidence in ['中', '低']

    def test_conservative_high_weight_requirements(self, evaluator, limit_up_event):
        """测试保守型高权重要求"""
        etf_holding = create_candidate_etf('510300', weight=0.15, rank=1)

        confidence, risk = evaluator.evaluate(limit_up_event, etf_holding)

        assert confidence == '高'


@pytest.mark.unit
class TestAggressiveEvaluator:
    """测试AggressiveEvaluator"""

    @pytest.fixture
    def evaluator(self):
        """创建激进型评估器"""
        config = SignalEvaluationConfig()
        return AggressiveEvaluator(config)

    @pytest.fixture
    def limit_up_event(self):
        """创建涨停事件"""
        return create_mock_limit_up_event('600519', '贵州茅台')

    def test_aggressive_more_lenient(self, evaluator, limit_up_event):
        """测试激进型评估器更宽松"""
        # 0.03权重在默认评估器应该是低置信度
        # 但在激进型评估器可能是中等置信度
        etf_holding = create_candidate_etf('510300', weight=0.03, rank=5)

        confidence, risk = evaluator.evaluate(limit_up_event, etf_holding)

        # 激进型评估器>=0.03权重就给中等置信度
        assert confidence in ['中', '高']


@pytest.mark.unit
class TestSignalEvaluatorFactory:
    """测试SignalEvaluatorFactory"""

    def test_create_default_evaluator(self):
        """测试创建默认评估器"""
        from backend.signal.evaluator import SignalEvaluatorFactory

        evaluator = SignalEvaluatorFactory.create('default')

        assert isinstance(evaluator, DefaultSignalEvaluator)

    def test_create_conservative_evaluator(self):
        """测试创建保守型评估器"""
        from backend.signal.evaluator import SignalEvaluatorFactory

        evaluator = SignalEvaluatorFactory.create('conservative')

        assert isinstance(evaluator, ConservativeEvaluator)

    def test_create_aggressive_evaluator(self):
        """测试创建激进型评估器"""
        from backend.signal.evaluator import SignalEvaluatorFactory

        evaluator = SignalEvaluatorFactory.create('aggressive')

        assert isinstance(evaluator, AggressiveEvaluator)

    def test_create_unknown_type_raises_error(self):
        """测试创建未知类型抛出异常"""
        from backend.signal.evaluator import SignalEvaluatorFactory

        with pytest.raises(ValueError, match="未知的评估器类型"):
            SignalEvaluatorFactory.create('unknown_type')

    def test_list_available_returns_evaluator_names(self):
        """测试列出可用评估器"""
        from backend.signal.evaluator import SignalEvaluatorFactory

        names = SignalEvaluatorFactory.list_available()

        assert isinstance(names, list)
        assert 'default' in names
        assert 'conservative' in names
        assert 'aggressive' in names
