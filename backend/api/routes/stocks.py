"""
股票和ETF数据路由

提供股票行情、相关ETF、涨停股、K线数据等端点
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from backend.api.dependencies import get_monitor, get_limit_up_cache
from backend.api.models import StockQuoteResponse, LimitUpStockResponse
from backend.data.limit_up_stocks import LimitUpStocksFetcher
from backend.data.kline import KlineDataFetcher
from backend.data.etf_holdings import ETFHoldingsFetcher

router = APIRouter()


@router.get("/api/stocks", response_model=list[StockQuoteResponse])
async def get_stocks():
    """
    获取所有自选股的实时行情

    Returns:
        自选股行情列表
    """
    mon = get_monitor()
    stock_codes = [s.code for s in mon.watch_stocks]

    quotes = mon.stock_fetcher.get_batch_quotes(stock_codes)

    result = []
    for code in stock_codes:
        quote = quotes.get(code)
        if quote:
            result.append(StockQuoteResponse(
                code=quote['code'],
                name=quote['name'],
                price=quote['price'],
                change_pct=quote['change_pct'],
                is_limit_up=quote['is_limit_up']
            ))

    return result


@router.get("/api/stocks/{code}/related-etfs")
async def get_related_etfs(code: str):
    """
    获取股票相关的ETF列表

    只返回该股票持仓占比 >= 5% 的 ETF，确保策略有效性

    Args:
        code: 股票代码

    Returns:
        相关ETF列表（仅包含持仓>=5%的ETF）
    """
    mon = get_monitor()

    # 使用带真实权重验证的方法，只返回持仓占比 >= 5% 的 ETF
    etfs = mon.find_related_etfs_with_real_weight(code)

    # 如果没有符合条件的ETF，返回空列表
    if not etfs:
        return []

    # 获取ETF实时行情
    etf_codes = [e['etf_code'] for e in etfs]
    quotes = mon.etf_fetcher.get_etf_batch_quotes(etf_codes)

    result = []
    for etf in etfs:
        etf_code = etf['etf_code']
        quote = quotes.get(etf_code)
        if quote:
            result.append({
                "etf_code": etf_code,
                "etf_name": etf['etf_name'],
                "weight": etf['weight'],
                "rank": etf.get('rank', -1),
                "in_top10": etf.get('in_top10', False),
                "category": etf.get('category', '宽基'),
                "price": quote['price'],
                "change_pct": quote['change_pct'],
                "volume": quote['amount'],
                "premium": quote.get('premium')
            })
        else:
            # 即使获取不到行情，也返回基本信息
            result.append({
                "etf_code": etf_code,
                "etf_name": etf['etf_name'],
                "weight": etf['weight'],
                "rank": etf.get('rank', -1),
                "in_top10": etf.get('in_top10', False),
                "category": etf.get('category', '宽基'),
                "price": 0,
                "change_pct": 0,
                "volume": 0,
                "premium": None
            })

    return result


@router.get("/api/limit-up", response_model=list[LimitUpStockResponse])
async def get_limit_up_stocks():
    """
    获取今日所有涨停股票（带缓存，复用股票行情缓存）

    Returns:
        涨停股票列表
    """
    cache = get_limit_up_cache()

    # 使用TTLCache组件
    def load_limit_up_stocks():
        """加载涨停股数据"""
        fetcher = LimitUpStocksFetcher()

        # 尝试从监控器获取缓存的股票数据
        try:
            mon = get_monitor()
            stock_df = mon.stock_fetcher._get_spot_data()
            stocks = fetcher.get_today_limit_ups(stock_df)
        except Exception as e:
            logger.warning(f"Failed to get cached spot data, using fresh fetch: {e}")
            stocks = fetcher.get_today_limit_ups()

        return [
            LimitUpStockResponse(
                code=s['code'],
                name=s['name'],
                price=s['price'],
                change_pct=s['change_pct'],
                volume=s['volume'],
                amount=s['amount'],
                turnover=s['turnover'],
                limit_time=s['limit_time'],
                locked_amount=s.get('locked_amount', 0)
            )
            for s in stocks
        ]

    # 使用统一的缓存组件
    return cache.get_or_load("limit_up_stocks", load_limit_up_stocks)


@router.get("/api/stocks/{code}/kline")
async def get_stock_kline(code: str, days: int = 60):
    """
    获取股票K线数据

    Args:
        code: 股票代码
        days: 天数

    Returns:
        K线数据
    """
    fetcher = KlineDataFetcher()
    kline_data = fetcher.get_kline_for_chart(code, days)

    if not kline_data:
        raise HTTPException(status_code=404, detail="无法获取K线数据")

    return kline_data


@router.get("/api/etfs/{code}/kline")
async def get_etf_kline(code: str, days: int = 60):
    """
    获取ETF K线数据

    Args:
        code: ETF代码
        days: 天数

    Returns:
        K线数据
    """
    fetcher = KlineDataFetcher()
    kline_data = fetcher.get_etf_kline(code, days)

    if not kline_data:
        raise HTTPException(status_code=404, detail="无法获取K线数据")

    return kline_data


@router.get("/api/etfs/{code}/holdings")
async def get_etf_holdings(code: str):
    """
    获取ETF的前十大持仓

    Args:
        code: ETF代码

    Returns:
        ETF持仓信息
    """
    fetcher = ETFHoldingsFetcher()
    holdings = fetcher.get_etf_top_holdings(code)

    return {
        "etf_code": holdings['etf_code'],
        "etf_name": holdings['etf_name'],
        "top_holdings": holdings['top_holdings'],
        "total_weight": holdings['total_weight']
    }


@router.get("/api/etfs/categories")
async def get_etf_categories():
    """
    获取所有ETF分类

    Returns:
        ETF分类数据
    """
    fetcher = ETFHoldingsFetcher()
    categories = fetcher.get_all_etfs_by_category()

    return categories
