"""
策略模板定义

提供预定义的回测策略配置模板，方便用户快速选择
"""

from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class StrategyTemplate:
    """策略模板"""
    id: str  # conservative, balanced, aggressive
    name: str  # 保守型, 平衡型, 激进型
    description: str
    min_weight: float
    min_etf_volume: float  # 万元
    min_order_amount: float  # 亿元
    evaluator_type: str

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "min_weight": self.min_weight,
            "min_etf_volume": self.min_etf_volume,
            "min_order_amount": self.min_order_amount,
            "evaluator_type": self.evaluator_type
        }


# 预定义策略模板
STRATEGY_TEMPLATES: Dict[str, StrategyTemplate] = {
    "conservative": StrategyTemplate(
        id="conservative",
        name="保守型",
        description="更严格的筛选，信号少但质量高",
        min_weight=0.08,
        min_etf_volume=8000,
        min_order_amount=15,
        evaluator_type="conservative"
    ),
    "balanced": StrategyTemplate(
        id="balanced",
        name="平衡型",
        description="推荐设置，平衡信号数量和质量",
        min_weight=0.05,
        min_etf_volume=5000,
        min_order_amount=10,
        evaluator_type="default"
    ),
    "aggressive": StrategyTemplate(
        id="aggressive",
        name="激进型",
        description="更多信号，可能包含低质量机会",
        min_weight=0.03,
        min_etf_volume=3000,
        min_order_amount=5,
        evaluator_type="aggressive"
    ),
}


def get_template(template_id: str) -> Optional[StrategyTemplate]:
    """获取指定模板

    Args:
        template_id: 模板ID (conservative, balanced, aggressive)

    Returns:
        StrategyTemplate或None
    """
    return STRATEGY_TEMPLATES.get(template_id)


def get_all_templates() -> List[StrategyTemplate]:
    """获取所有模板

    Returns:
        模板列表
    """
    return list(STRATEGY_TEMPLATES.values())
