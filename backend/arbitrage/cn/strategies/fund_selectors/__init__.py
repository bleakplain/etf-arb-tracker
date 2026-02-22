"""
基金选择策略包

定义各种基金（ETF/LOF等）选择策略：
- HighestWeightSelector: 选择权重最高的
- BestLiquiditySelector: 选择流动性最好的
- LowestPremiumSelector: 选择溢价最低的
- BalancedSelector: 综合评估选择
"""

from backend.arbitrage.cn.strategies.fund_selectors.highest_weight import HighestWeightSelector
from backend.arbitrage.cn.strategies.fund_selectors.best_liquidity import BestLiquiditySelector
from backend.arbitrage.cn.strategies.fund_selectors.lowest_premium import LowestPremiumSelector
from backend.arbitrage.cn.strategies.fund_selectors.balanced import BalancedSelector

__all__ = [
    'HighestWeightSelector',
    'BestLiquiditySelector',
    'LowestPremiumSelector',
    'BalancedSelector',
]
