"""测试策略模板"""
import pytest
from backend.backtest.strategy_templates import (
    StrategyTemplate,
    get_template,
    get_all_templates,
    STRATEGY_TEMPLATES
)


def test_conservative_template_exists():
    """保守型模板存在且有正确的参数"""
    template = get_template("conservative")
    assert template is not None
    assert template.id == "conservative"
    assert template.name == "保守型"
    assert template.min_weight == 0.08
    assert template.min_etf_volume == 8000
    assert template.evaluator_type == "conservative"


def test_balanced_template_is_default():
    """平衡型模板是推荐默认值"""
    template = get_template("balanced")
    assert template.id == "balanced"
    assert template.min_weight == 0.05
    assert template.min_etf_volume == 5000


def test_aggressive_template_has_lower_thresholds():
    """激进型模板有更低的阈值"""
    template = get_template("aggressive")
    assert template.min_weight == 0.03
    assert template.min_etf_volume == 3000


def test_get_all_templates_returns_three():
    """获取所有模板返回3个"""
    templates = get_all_templates()
    assert len(templates) == 3
    ids = [t.id for t in templates]
    assert "conservative" in ids
    assert "balanced" in ids
    assert "aggressive" in ids


def test_invalid_template_returns_none():
    """无效模板ID返回None"""
    template = get_template("invalid")
    assert template is None


def test_template_to_dict():
    """模板可以转换为字典（用于API响应）"""
    template = get_template("balanced")
    data = template.to_dict()
    assert isinstance(data, dict)
    assert data["id"] == "balanced"
    assert data["min_weight"] == 0.05
