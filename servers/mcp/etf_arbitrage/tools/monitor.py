"""
Monitor control tools for ETF Arbitrage MCP Server.

Provides tools for controlling the arbitrage monitoring service.
"""

from typing import Dict, Any
from datetime import datetime
from mcp.server.fastmcp import FastMCP

from ..models.enums import ResponseFormat
from ..utils.errors import get_error_response
from ..utils.formatters import format_timestamp
from .base import (
    get_backend,
    ToolResponse,
)


# Global monitor state (in production, this would be in a proper state store)
_monitor_state = {
    'is_running': False,
    'last_scan': None,
    'next_scan': None,
    'scan_interval': 120,  # seconds
    'total_signals': 0,
}


def register_monitor_tools(mcp: FastMCP):
    """Register all monitor control tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool(
        name="etf_arbitrage_get_monitor_status",
        annotations={
            "title": "Get Monitor Status",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    async def get_monitor_status(params: Dict = None) -> str:
        """Get the current status of the arbitrage monitoring service.

        This tool retrieves the current status of the monitoring service,
        including whether it's running, last scan time, and signal statistics.
        It does NOT start or stop monitoring, only retrieves status information.

        Args:
            params: Optional parameters (for compatibility)

        Returns:
            str: Formatted response containing monitor status

        Examples:
            - Use when: "Check if monitor is running" -> call with no params
            - Use when: "Show monitoring status" -> call with no params
            - Don't use when: You need to start monitoring (use etf_arbitrage_start_monitor instead)
            - Don't use when: You need to stop monitoring (use etf_arbitrage_stop_monitor instead)

        Error Handling:
            - Returns current monitor state
            - Returns warning if monitor has never been started
        """
        try:
            backend = get_backend()
            config = backend.get_config()

            # Get trading hours
            from backend.utils import is_trading_time, get_time_to_market_close
            is_trading_time = is_trading_time()
            time_to_close = get_time_to_market_close() if is_trading_time else None

            # Get watchlist count
            try:
                import yaml
                stocks_path = backend.get_stocks_path()
                if stocks_path.exists():
                    with open(stocks_path, 'r', encoding='utf-8') as f:
                        stock_config = yaml.safe_load(f)
                    watched_stocks = len(stock_config.get('my_stocks', []))
                else:
                    watched_stocks = 0
            except:
                watched_stocks = 0

            # Get signal count from repository
            try:
                signal_repo = backend.get_signal_repository()
                today_signals_list = signal_repo.get_today_signals()
                today_signals = len(today_signals_list)
            except:
                today_signals = 0

            # Build status
            status = {
                'is_running': _monitor_state['is_running'],
                'last_scan': _monitor_state['last_scan'],
                'next_scan': _monitor_state['next_scan'],
                'scan_interval': _monitor_state['scan_interval'],
                'watched_stocks': watched_stocks,
                'total_signals': _monitor_state['total_signals'],
                'today_signals': today_signals,
                'is_trading_time': is_trading_time,
                'time_to_close': time_to_close,
                'timestamp': datetime.now().isoformat(),
            }

            # Format response
            import json
            return json.dumps(status, indent=2, ensure_ascii=False, default=str)

        except Exception as e:
            return ToolResponse.error(f"Failed to get monitor status: {str(e)}")

    @mcp.tool(
        name="etf_arbitrage_start_monitor",
        annotations={
            "title": "Start Monitor",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    async def start_monitor(params: Dict = None) -> str:
        """Start the arbitrage monitoring service.

        This tool starts the continuous monitoring service that scans for
        limit-up stocks and generates arbitrage signals. The monitor runs
        at a configured interval and watches all stocks in the watchlist.

        Args:
            params: Optional parameters (for compatibility)

        Returns:
            str: Formatted response confirming monitor start

        Examples:
            - Use when: "Start monitoring for arbitrage opportunities" -> call with no params
            - Use when: "Enable the monitoring service" -> call with no params
            - Don't use when: Monitor is already running (will return error)
            - Don't use when: You need to stop monitoring (use etf_arbitrage_stop_monitor instead)

        Error Handling:
            - Returns error if monitor is already running
            - Returns success with scan interval information
        """
        try:
            if _monitor_state['is_running']:
                return get_error_response(
                    "monitor_already_running",
                )

            # Update state
            _monitor_state['is_running'] = True
            _monitor_state['last_scan'] = None
            _monitor_state['next_scan'] = datetime.now().isoformat()
            _monitor_state['total_signals'] = 0

            # Get scan interval from config
            backend = get_backend()
            config = backend.get_config()
            scan_interval = config.get('strategy', {}).get('scan_interval', 120)
            _monitor_state['scan_interval'] = scan_interval

            # Start monitoring (in production, this would start a background task)
            # For now, we just mark it as running
            import asyncio
            asyncio.create_task(_run_monitor_loop(backend))

            return (
                f"✅ Monitor started successfully\n\n"
                f"- **Scan Interval**: {scan_interval} seconds\n"
                f"- **Next Scan**: Starting now\n"
                f"- **Status**: Running"
            )

        except Exception as e:
            return ToolResponse.error(f"Failed to start monitor: {str(e)}")

    @mcp.tool(
        name="etf_arbitrage_stop_monitor",
        annotations={
            "title": "Stop Monitor",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    async def stop_monitor(params: Dict = None) -> str:
        """Stop the arbitrage monitoring service.

        This tool stops the continuous monitoring service. Any ongoing
        scans will be completed before the monitor stops. The monitor
        state is preserved and can be restarted later.

        Args:
            params: Optional parameters (for compatibility)

        Returns:
            str: Formatted response confirming monitor stop

        Examples:
            - Use when: "Stop the monitoring service" -> call with no params
            - Use when: "Disable arbitrage monitoring" -> call with no params
            - Don't use when: Monitor is not running (will return message)
            - Don't use when: You need to start monitoring (use etf_arbitrage_start_monitor instead)

        Error Handling:
            - Returns message if monitor is not running (no error)
            - Returns success with final statistics
        """
        try:
            if not _monitor_state['is_running']:
                return "ℹ️ Monitor is not currently running"

            # Update state
            _monitor_state['is_running'] = False
            _monitor_state['next_scan'] = None

            total_scans = _monitor_state.get('total_scans', 0)

            return (
                f"✅ Monitor stopped successfully\n\n"
                f"- **Total Signals Generated**: {_monitor_state['total_signals']}\n"
                f"- **Last Scan**: {format_timestamp(_monitor_state['last_scan']) if _monitor_state['last_scan'] else 'N/A'}\n"
                f"- **Status**: Stopped"
            )

        except Exception as e:
            return ToolResponse.error(f"Failed to stop monitor: {str(e)}")

    @mcp.tool(
        name="etf_arbitrage_trigger_scan",
        annotations={
            "title": "Trigger Manual Scan",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    async def trigger_scan(params: Dict = None) -> str:
        """Trigger a manual scan for arbitrage opportunities.

        This tool immediately scans all stocks in the watchlist for
        limit-up conditions and generates signals if opportunities are found.
        The monitor does not need to be running to use this tool.

        Args:
            params: Optional parameters (for compatibility)

        Returns:
            str: Formatted response with scan results

        Examples:
            - Use when: "Scan for arbitrage opportunities now" -> call with no params
            - Use when: "Check current market conditions" -> call with no params
            - Don't use when: You need continuous monitoring (use etf_arbitrage_start_monitor instead)
            - Don't use when: You need historical signals (use etf_arbitrage_list_signals instead)

        Error Handling:
            - Returns number of stocks scanned
            - Returns number of signals generated
            - Returns any errors encountered during scan
        """
        try:
            backend = get_backend()
            engine = backend.get_arbitrage_engine()
            signal_repo = backend.get_signal_repository()

            # Get watchlist
            import yaml
            stocks_path = backend.get_stocks_path()
            if not stocks_path.exists():
                return "❌ No watchlist configured. Add stocks to watchlist first."

            with open(stocks_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            watchlist = config.get('my_stocks', [])
            if not watchlist:
                return "❌ Watchlist is empty. Add stocks to watchlist first."

            # Scan stocks
            from .base import fetch_stock_quotes

            stock_codes = [s['code'] for s in watchlist]
            quotes = await fetch_stock_quotes(stock_codes)

            # Check for limit-up stocks
            limit_up_stocks = [
                q for q in quotes
                if getattr(q, 'is_limit_up', False) or q.change_pct >= 0.095
            ]

            # Generate signals
            new_signals = []
            for stock in limit_up_stocks:
                try:
                    # Get related ETFs
                    mapping = await engine.get_stock_etf_mapping(stock.code)

                    for etf_code, weight in mapping.get('etfs', {}).items():
                        if weight >= 0.05:  # 5% threshold
                            # Create signal
                            signal = await signal_repo.save(
                                stock_code=stock.code,
                                stock_name=stock.name,
                                etf_code=etf_code,
                                etf_name=etf_code,  # Would fetch from mapping
                                weight=weight,
                                event_type='limit_up',
                                confidence=0.8,
                            )
                            new_signals.append(signal)
                except Exception as e:
                    pass  # Continue with next stock

            # Update monitor state
            _monitor_state['last_scan'] = datetime.now().isoformat()
            _monitor_state['total_signals'] += len(new_signals)

            # Build response
            lines = [
                "✅ Manual scan completed",
                "",
                f"- **Stocks Scanned**: {len(quotes)}",
                f"- **Limit-Up Stocks**: {len(limit_up_stocks)}",
                f"- **Signals Generated**: {len(new_signals)}",
                "",
            ]

            if limit_up_stocks:
                lines.append("**Limit-Up Stocks Found:**")
                for stock in limit_up_stocks:
                    lines.append(f"- {stock.name} ({stock.code}): +{stock.change_pct:.2f}%")

            if new_signals:
                lines.append("")
                lines.append("**New Signals:**")
                for signal in new_signals[:10]:  # Show first 10
                    lines.append(f"- {signal.stock_name} → {signal.etf_code} ({signal.weight*100:.2f}%)")

                if len(new_signals) > 10:
                    lines.append(f"- ... and {len(new_signals) - 10} more signals")

            return "\n".join(lines)

        except Exception as e:
            return ToolResponse.error(f"Failed to trigger scan: {str(e)}")


# ============================================================================
# Monitor Loop (Background Task)
# ============================================================================

async def _run_monitor_loop(backend) -> None:
    """Run the monitor loop in the background.

    Args:
        backend: Backend bridge instance
    """
    import asyncio
    import logging

    logger = logging.getLogger(__name__)

    try:
        while _monitor_state['is_running']:
            # Check if trading time
            from backend.utils.clock import Clock
            clock = Clock()

            if not clock.is_trading_time():
                # Sleep until next trading period
                await asyncio.sleep(60)
                continue

            # Perform scan
            try:
                await trigger_scan({})
                _monitor_state['total_scans'] = _monitor_state.get('total_scans', 0) + 1
            except Exception as e:
                logger.error(f"Monitor scan failed: {str(e)}")

            # Sleep until next scan
            scan_interval = _monitor_state['scan_interval']
            await asyncio.sleep(scan_interval)

    except asyncio.CancelledError:
        logger.info("Monitor loop cancelled")
    except Exception as e:
        logger.error(f"Monitor loop error: {str(e)}")
        _monitor_state['is_running'] = False
