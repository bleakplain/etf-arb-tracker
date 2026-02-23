"""
信号路由

提供交易信号历史查询端点
"""

from fastapi import APIRouter
from datetime import datetime

from backend.api.dependencies import get_engine
from backend.api.models import SignalResponse

router = APIRouter()


@router.get("/api/signals", response_model=list[SignalResponse])
async def get_signals(limit: int = 20, today_only: bool = True):
    """
    获取信号历史

    Args:
        limit: 返回数量限制
        today_only: 是否只返回今天的信号

    Returns:
        信号列表
    """
    engine = get_engine()

    signals = engine.signal_history

    if today_only:
        today = datetime.now().strftime("%Y-%m-%d")
        signals = [s for s in signals if s.timestamp.startswith(today)]

    # 按时间倒序
    signals = sorted(signals, key=lambda x: x.timestamp, reverse=True)

    # 限制数量
    signals = signals[:limit]

    return [
        SignalResponse(
            signal_id=s.signal_id,
            timestamp=s.timestamp,
            stock_code=s.stock_code,
            stock_name=s.stock_name,
            stock_price=s.stock_price,
            etf_code=s.etf_code,
            etf_name=s.etf_name,
            etf_price=s.etf_price,
            etf_weight=s.etf_weight,
            confidence=s.confidence,
            risk_level=s.risk_level,
            reason=s.reason
        )
        for s in signals
    ]
