"""
Arbitrage analysis tools for ETF Arbitrage MCP Server.

Provides tools for finding related ETFs and analyzing arbitrage opportunities.
"""

from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP

from ..models.requests import (
    FindRelatedETFsRequest,
    AnalyzeOpportunityRequest,
)
from ..models.enums import ResponseFormat
from ..utils.formatters import ETFFormatter, StockFormatter
from ..utils.errors import get_error_response
from .base import (
    get_backend,
    ToolResponse,
    fetch_stock_quotes,
    get_etf_info,
)


def register_arbitrage_tools(mcp: FastMCP):
    """Register all arbitrage analysis tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool(
        name="etf_arbitrage_find_related_etfs",
        annotations={
            "title": "Find Related ETFs",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }
    )
    async def find_related_etfs_tool(params: FindRelatedETFsRequest) -> str:
        """Find ETFs that hold a specific stock above a weight threshold.

        This tool searches for ETFs that have the specified stock in their
        holdings with weight above the minimum threshold. These ETFs represent
        potential arbitrage opportunities when the stock is limit-up.

        Args:
            params (FindRelatedETFsRequest): Validated input parameters containing:
                - stock_code (str): Stock code (6 digits, e.g., '600519')
                - min_weight (float): Minimum weight threshold (0.01-1.0, default=0.05 for 5%)
                - response_format (ResponseFormat): Output format ('markdown' or 'json', default='markdown')

        Returns:
            str: Formatted response containing related ETFs with the following schema:

            Success response (Markdown):
            # Related ETFs for 贵州茅台 (600519)
            Found 3 ETFs with weight >= 5.00%

            ## 沪深300ETF (510300)
            - **Weight**: 5.20%
            - **Market**: SH
            - **Category**: 宽基指数
            - **Premium Rate**: +0.15%
            - **Daily Amount**: 25,000,000.00

            ## 50ETF (510050)
            - **Weight**: 3.80%
            - **Market**: SH
            - **Category**: 宽基指数
            - **Premium Rate**: -0.05%
            - **Daily Amount**: 15,000,000.00

            Success response (JSON):
            {
              "stock_code": "600519",
              "stock_name": "贵州茅台",
              "min_weight": 0.05,
              "etfs": [
                {
                  "code": "510300",
                  "name": "沪深300ETF",
                  "weight": 0.052,
                  "weight_pct": 5.20,
                  "market": "sh",
                  "premium_rate": 0.15
                }
              ],
              "total_etfs": 3
            }

            Error response:
            "Error: No ETFs found holding stock '600519' above weight threshold. Suggestion: Try lowering the min_weight parameter (current: 0.05)"

        Examples:
            - Use when: "Find ETFs that hold Kweichow Moutai" -> params with stock_code='600519'
            - Use when: "Which ETFs have China Merchants Bank with 3%+ weight?" -> params with stock_code='600036', min_weight=0.03
            - Don't use when: You need real-time stock quote (use etf_arbitrage_get_stock_quote instead)
            - Don't use when: You need full arbitrage analysis (use etf_arbitrage_analyze_opportunity instead)

        Error Handling:
            - Input validation errors are handled by Pydantic model
            - Returns error if stock code not found
            - Returns error if no ETFs found above threshold (with suggestion to lower threshold)
        """
        try:
            backend = get_backend()
            engine = backend.get_arbitrage_engine()

            # Get stock info first
            stock_info = None
            try:
                quotes = await fetch_stock_quotes([params.stock_code])
                if quotes:
                    stock_info = quotes[0]
            except:
                pass

            # Get mapping
            mapping_repo = backend.get_mapping_repository()
            etf_list = mapping_repo.get_etf_list(params.stock_code)

            # Filter by weight
            related_etfs = []
            for etf_info in etf_list:
                weight = etf_info.get('weight', etf_info.get('etf_weight', 0))
                if weight >= params.min_weight:
                    # Get ETF details
                    try:
                        full_etf_info = await get_etf_info(etf_info['code'])
                        full_etf_info['weight'] = weight
                        full_etf_info['weight_pct'] = weight * 100
                        related_etfs.append(full_etf_info)
                    except:
                        # If we can't get full info, use basic entry
                        related_etfs.append({
                            'code': etf_info['code'],
                            'name': etf_info.get('name', etf_info['code']),
                            'weight': weight,
                            'weight_pct': weight * 100,
                            'market': etf_info.get('market', 'unknown'),
                        })

            if not related_etfs:
                return get_error_response(
                    "no_related_etfs",
                    code=params.stock_code,
                    weight=params.min_weight * 100
                )

            # Sort by weight descending
            related_etfs.sort(key=lambda x: x['weight'], reverse=True)

            # Build response
            stock_name = stock_info.name if stock_info else params.stock_code

            if params.response_format == ResponseFormat.JSON:
                import json
                response = {
                    'stock_code': params.stock_code,
                    'stock_name': stock_name,
                    'min_weight': params.min_weight,
                    'etfs': related_etfs,
                    'total_etfs': len(related_etfs),
                }
                return json.dumps(response, indent=2, ensure_ascii=False, default=str)

            # Markdown format
            min_weight_pct = params.min_weight * 100
            lines = [
                f"# Related ETFs for {stock_name} ({params.stock_code})",
                "",
                f"Found {len(related_etfs)} ETFs with weight >= {min_weight_pct:.2f}%",
                ""
            ]

            for etf in related_etfs:
                lines.append(f"## {etf['name']} ({etf['code']})")
                lines.append(f"- **Weight**: {etf['weight_pct']:.2f}%")
                lines.append(f"- **Market**: {etf['market'].upper()}")

                if etf.get('category'):
                    lines.append(f"- **Category**: {etf['category']}")

                if etf.get('premium_rate') is not None:
                    lines.append(f"- **Premium Rate**: {etf['premium_rate']:+.2f}%")

                if etf.get('daily_amount'):
                    lines.append(f"- **Daily Amount**: {etf['daily_amount']:,.2f}")

                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return ToolResponse.error(f"Failed to find related ETFs: {str(e)}")

    @mcp.tool(
        name="etf_arbitrage_analyze_opportunity",
        annotations={
            "title": "Analyze Arbitrage Opportunity",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }
    )
    async def analyze_opportunity(params: AnalyzeOpportunityRequest) -> str:
        """Analyze arbitrage opportunity for a specific stock.

        This tool provides comprehensive analysis of arbitrage opportunities,
        including stock status, related ETFs, and recent signals. It helps
        evaluate whether buying an ETF is a viable alternative when the stock
        is limit-up.

        Args:
            params (AnalyzeOpportunityRequest): Validated input parameters containing:
                - stock_code (str): Stock code (6 digits, e.g., '600519')
                - include_signals (bool): Whether to include recent signals (default=True)
                - response_format (ResponseFormat): Output format ('markdown' or 'json', default='markdown')

        Returns:
            str: Formatted arbitrage opportunity analysis

        Examples:
            - Use when: "Analyze arbitrage opportunity for Kweichow Moutai" -> params with stock_code='600519'
            - Use when: "Should I buy ETF instead of 600036?" -> params with stock_code='600036'
            - Don't use when: You only need related ETFs list (use etf_arbitrage_find_related_etfs instead)
            - Don't use when: You need stock quote without analysis (use etf_arbitrage_get_stock_quote instead)

        Error Handling:
            - Returns error if stock code not found
            - Returns analysis with warning if stock is not limit-up
        """
        try:
            backend = get_backend()
            engine = backend.get_arbitrage_engine()
            signal_repo = backend.get_signal_repository()

            # Get stock quote
            stock_quotes = await fetch_stock_quotes([params.stock_code])
            if not stock_quotes:
                return get_error_response("stock_not_found", code=params.stock_code)

            stock = stock_quotes[0]
            stock_dict = {
                'code': stock.code,
                'name': stock.name,
                'price': stock.price,
                'change': stock.change,
                'change_pct': stock.change_pct,
                'is_limit_up': getattr(stock, 'is_limit_up', False),
                'market': stock.market,
            }

            # Get related ETFs
            mapping_repo = backend.get_mapping_repository()
            etf_list = mapping_repo.get_etf_list(params.stock_code)
            related_etfs = []

            for etf_info in etf_list:
                weight = etf_info.get('weight', etf_info.get('etf_weight', 0))
                if weight >= 0.05:  # 5% threshold
                    try:
                        full_etf_info = await get_etf_info(etf_info['code'])
                        full_etf_info['weight'] = weight
                        full_etf_info['weight_pct'] = weight * 100
                        related_etfs.append(full_etf_info)
                    except:
                        related_etfs.append({
                            'code': etf_info['code'],
                            'name': etf_info.get('name', etf_info['code']),
                            'weight': weight,
                            'weight_pct': weight * 100,
                            'market': etf_info.get('market', 'unknown'),
                        })

            # Sort by weight
            related_etfs.sort(key=lambda x: x['weight'], reverse=True)

            # Get recent signals if requested
            recent_signals = []
            if params.include_signals:
                try:
                    signals = signal_repo.get_signals_by_stock(
                        params.stock_code,
                        limit=5
                    )
                    recent_signals = [s.signal_id for s in signals]
                except:
                    pass

            # Find best ETF
            best_etf = related_etfs[0] if related_etfs else None

            # Build analysis
            from datetime import datetime
            analysis = {
                'stock_code': params.stock_code,
                'stock_name': stock.name,
                'is_limit_up': stock_dict['is_limit_up'],
                'change_pct': stock.change_pct,
                'related_etfs': related_etfs,
                'best_etf': best_etf,
                'recent_signals': recent_signals,
                'analysis_timestamp': datetime.now().isoformat(),
            }

            if params.response_format == ResponseFormat.JSON:
                import json
                return json.dumps(analysis, indent=2, ensure_ascii=False, default=str)

            # Markdown format
            status_emoji = "🔴" if stock_dict['is_limit_up'] else "📊"
            lines = [
                f"# Arbitrage Opportunity Analysis",
                "",
                f"## Stock: {stock.name} ({params.stock_code}) {status_emoji}",
                "",
                f"- **Current Price**: {stock.price:.2f}",
                f"- **Change**: {stock.change:+.2f} ({stock.change_pct:+.2f}%)",
                f"- **Status**: {'🔴 LIMIT-UP - Consider buying ETF!' if stock_dict['is_limit_up'] else 'Not limit-up'}",
                "",
            ]

            if related_etfs:
                lines.append(f"## Related ETFs ({len(related_etfs)})")
                lines.append("")
                lines.append(f"### ⭐ Recommended: {best_etf['name']} ({best_etf['code']})")
                lines.append(f"- **Weight**: {best_etf['weight_pct']:.2f}%")
                if best_etf.get('premium_rate') is not None:
                    lines.append(f"- **Premium Rate**: {best_etf['premium_rate']:+.2f}%")
                lines.append("")
                lines.append("**Other Related ETFs:**")
                lines.append("")

                for etf in related_etfs[1:]:
                    lines.append(f"- **{etf['name']} ({etf['code']})**: {etf['weight_pct']:.2f}%")
            else:
                lines.append("## Related ETFs")
                lines.append("")
                lines.append("No ETFs found with >= 5% weight.")

            if recent_signals:
                lines.append("")
                lines.append("## Recent Signals")
                lines.append("")
                for sig_id in recent_signals:
                    lines.append(f"- Signal {sig_id[:8]}")

            lines.append("")
            lines.append(f"*Analysis generated at {analysis['analysis_timestamp']}*")

            return "\n".join(lines)

        except Exception as e:
            return ToolResponse.error(f"Failed to analyze opportunity: {str(e)}")
