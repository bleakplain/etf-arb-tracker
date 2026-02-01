"""测试回测模板API"""
import pytest
from fastapi.testclient import TestClient

# Import the app
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.api.app import app

client = TestClient(app)


def test_get_strategy_templates_success():
    """成功获取策略模板列表"""
    response = client.get("/api/backtest/templates")
    assert response.status_code == 200

    data = response.json()
    assert "templates" in data
    assert len(data["templates"]) == 3

    # 验证保守型模板
    conservative = next(t for t in data["templates"] if t["id"] == "conservative")
    assert conservative["name"] == "保守型"
    assert conservative["min_weight"] == 0.08

    # 验证平衡型模板
    balanced = next(t for t in data["templates"] if t["id"] == "balanced")
    assert balanced["name"] == "平衡型"
    assert balanced["min_weight"] == 0.05

    # 验证激进型模板
    aggressive = next(t for t in data["templates"] if t["id"] == "aggressive")
    assert aggressive["name"] == "激进型"
    assert aggressive["min_weight"] == 0.03


def test_templates_include_descriptions():
    """模板包含描述信息"""
    response = client.get("/api/backtest/templates")
    data = response.json()

    for template in data["templates"]:
        assert "description" in template
        assert len(template["description"]) > 0
