"""
Backtesting tools for ETF Arbitrage MCP Server.

Provides tools for running backtests and retrieving results.
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from mcp.server.fastmcp import FastMCP

from ..models.requests import (
    RunBacktestRequest,
    GetBacktestResultRequest,
    ListBacktestsRequest,
)
from ..models.enums import (
    ResponseFormat,
    TimeGranularity,
    EventDetectorType,
    FundSelectorType,
    SignalFilterType,
)
from ..utils.errors import get_error_response, format_error
from ..utils.formatters import format_timestamp
from .base import (
    get_backend,
    ToolResponse,
)


def register_backtest_tools(mcp: FastMCP):
    """Register all backtesting tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool(
        name="etf_arbitrage_run_backtest",
        annotations={
            "title": "Run Backtest",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    async def run_backtest(params: RunBacktestRequest) -> str:
        """Run a backtest with specified parameters.

        This tool executes a backtest using historical data to evaluate
        arbitrage strategy performance. The backtest runs asynchronously
        and results can be retrieved using the returned job ID.

        Args:
            params (RunBacktestRequest): Validated input parameters containing:
                - start_date (str): Start date in YYYY-MM-DD format
                - end_date (str): End date in YYYY-MM-DD format
                - event_detector (EventDetectorType): Event detector strategy (default='limit_up_cn')
                - fund_selector (FundSelectorType): Fund selector strategy (default='highest_weight')
                - signal_filters (List[SignalFilterType]): Signal filters to apply
                - granularity (TimeGranularity): Time granularity (default='daily')
                - response_format (ResponseFormat): Output format ('markdown' or 'json', default='markdown')

        Returns:
            str: Formatted response containing job ID and status

        Examples:
            - Use when: "Run a backtest for January 2024" -> params with start_date='2024-01-01', end_date='2024-01-31'
            - Use when: "Backtest with lowest_premium strategy" -> params with fund_selector='lowest_premium'
            - Don't use when: You need to list existing backtests (use etf_arbitrage_list_backtests instead)
            - Don't use when: You need backtest results (use etf_arbitrage_get_backtest_result instead)

        Error Handling:
            - Validates date range (end must be after start)
            - Validates strategy parameters
            - Returns job ID for tracking backtest progress
        """
        try:
            # Validate date range
            start_dt = datetime.strptime(params.start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(params.end_date, "%Y-%m-%d")

            if start_dt >= end_dt:
                return get_error_response(
                    "invalid_date_range",
                    start=params.start_date,
                    end=params.end_date
                )

            backend = get_backend()
            backtest_engine = backend.get_backtest_engine()
            backtest_repo = backend.get_backtest_repository()

            # Map enum values to backend format
            granularity_map = {
                TimeGranularity.DAILY: "daily",
                TimeGranularity.MIN_5: "5m",
                TimeGranularity.MIN_15: "15m",
                TimeGranularity.MIN_30: "30m",
            }

            # Create backtest configuration
            config = {
                'start_date': params.start_date,
                'end_date': params.end_date,
                'event_detector': params.event_detector.value,
                'fund_selector': params.fund_selector.value,
                'signal_filters': [f.value for f in params.signal_filters],
                'granularity': granularity_map.get(params.granularity, 'daily'),
            }

            # Generate job ID
            job_id = str(uuid.uuid4())

            # Create backtest job data
            job_data = {
                'job_id': job_id,
                'config': config,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
            }

            # Save job
            backtest_repo.save_job(job_id, job_data)

            # Run backtest asynchronously
            import asyncio
            asyncio.create_task(_run_backtest_async(job_id, config, backend))

            # Build response
            result = {
                'job_id': job_id,
                'status': 'pending',
                'message': 'Backtest job created successfully',
                'config': config,
                'created_at': datetime.now().isoformat(),
            }

            if params.response_format == ResponseFormat.JSON:
                import json
                return json.dumps(result, indent=2, ensure_ascii=False, default=str)

            # Markdown format
            lines = [
                "# Backtest Job Created",
                "",
                f"**Job ID**: {job_id}",
                f"**Status**: Pending",
                f"**Created**: {result['created_at']}",
                "",
                "## Configuration",
                f"- **Date Range**: {params.start_date} to {params.end_date}",
                f"- **Event Detector**: {params.event_detector.value}",
                f"- **Fund Selector**: {params.fund_selector.value}",
                f"- **Signal Filters**: {', '.join([f.value for f in params.signal_filters])}",
                f"- **Granularity**: {params.granularity.value}",
                "",
                "## Next Steps",
                f"Use `etf_arbitrage_get_backtest_result` with job_id='{job_id}' to check results.",
            ]

            return "\n".join(lines)

        except ValueError as e:
            return ToolResponse.error(f"Invalid date format: {str(e)}", "Use YYYY-MM-DD format")
        except Exception as e:
            return ToolResponse.error(f"Failed to create backtest: {str(e)}")

    @mcp.tool(
        name="etf_arbitrage_get_backtest_result",
        annotations={
            "title": "Get Backtest Result",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    async def get_backtest_result(params: GetBacktestResultRequest) -> str:
        """Get results of a backtest job.

        This tool retrieves the results of a previously created backtest job,
        including generated signals and performance metrics. It does NOT
        create or modify backtests, only retrieves existing results.

        Args:
            params (GetBacktestResultRequest): Validated input parameters containing:
                - job_id (str): Backtest job ID (UUID format)
                - response_format (ResponseFormat): Output format ('markdown' or 'json', default='markdown')

        Returns:
            str: Formatted response containing backtest results

        Examples:
            - Use when: "Get results for backtest abc123" -> params with job_id='abc123-def456-...'
            - Use when: "Show performance metrics for this backtest" -> params with job_id
            - Don't use when: You need to create a new backtest (use etf_arbitrage_run_backtest instead)
            - Don't use when: You need to list all backtests (use etf_arbitrage_list_backtests instead)

        Error Handling:
            - Returns error if job_id not found
            - Returns results with status (pending/running/completed/failed)
        """
        try:
            backend = get_backend()
            backtest_repo = backend.get_backtest_repository()

            # Fetch job
            job = backtest_repo.load_job(params.job_id)

            if not job:
                return get_error_response("backtest_not_found", job_id=params.job_id)

            # Convert to dict format
            result = {
                'job_id': job.get('job_id'),
                'status': job.get('status'),
                'start_date': job.get('config', {}).get('start_date'),
                'end_date': job.get('config', {}).get('end_date'),
                'total_signals': len(job.get('signals', [])),
                'event_detector': job.get('config', {}).get('event_detector'),
                'fund_selector': job.get('config', {}).get('fund_selector'),
                'signal_filters': job.get('config', {}).get('signal_filters', []),
                'created_at': job.get('created_at'),
                'completed_at': job.get('completed_at'),
                'error': job.get('error') if job.get('status') == 'failed' else None,
            }

            # Add performance metrics if available
            if job.performance:
                result['performance'] = job.performance

            # Add signals if completed
            if job.signals and params.response_format == ResponseFormat.JSON:
                result['signals'] = [
                    {
                        'id': s.id,
                        'stock_code': s.stock_code,
                        'etf_code': s.etf_code,
                        'weight': s.weight,
                        'timestamp': s.timestamp.isoformat() if s.timestamp else None,
                    }
                    for s in job.signals
                ]

            # Build response
            if params.response_format == ResponseFormat.JSON:
                import json
                return json.dumps(result, indent=2, ensure_ascii=False, default=str)

            # Markdown format
            status_emoji = {
                'pending': '⏳',
                'running': '🔄',
                'completed': '✅',
                'failed': '❌',
            }.get(result['status'], '❓')

            lines = [
                f"# Backtest Results {status_emoji}",
                "",
                f"**Job ID**: {result['job_id']}",
                f"**Status**: {result['status'].upper()}",
                "",
                "## Configuration",
                f"- **Date Range**: {result['start_date']} to {result['end_date']}",
                f"- **Event Detector**: {result['event_detector']}",
                f"- **Fund Selector**: {result['fund_selector']}",
                f"- **Signal Filters**: {', '.join(result['signal_filters'])}",
                "",
                "## Summary",
                f"- **Total Signals**: {result['total_signals']}",
                f"- **Created**: {format_timestamp(result['created_at'])}",
            ]

            if result['completed_at']:
                lines.append(f"- **Completed**: {format_timestamp(result['completed_at'])}")

            if result.get('performance'):
                lines.append("")
                lines.append("## Performance Metrics")
                for key, value in result['performance'].items():
                    lines.append(f"- **{key}**: {value}")

            if result['error']:
                lines.append("")
                lines.append("## Error")
                lines.append(f"```\n{result['error']}\n```")

            if result['status'] == 'pending':
                lines.append("")
                lines.append("*Backtest is currently running. Check back later for results.*")

            return "\n".join(lines)

        except Exception as e:
            return ToolResponse.error(f"Failed to get backtest result: {str(e)}")

    @mcp.tool(
        name="etf_arbitrage_list_backtests",
        annotations={
            "title": "List Backtest Jobs",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    async def list_backtests(params: ListBacktestsRequest) -> str:
        """List backtest jobs with optional filtering.

        This tool retrieves a list of backtest jobs with their status and
        summary information. It does NOT create or modify backtests, only
        retrieves existing job records.

        Args:
            params (ListBacktestsRequest): Validated input parameters containing:
                - limit (int): Maximum results to return (1-100, default=20)
                - offset (int): Number of results to skip for pagination (default=0)
                - status (Optional[str]): Filter by status (pending/running/completed/failed)
                - response_format (ResponseFormat): Output format ('markdown' or 'json', default='markdown')

        Returns:
            str: Formatted response containing backtest jobs with pagination info

        Examples:
            - Use when: "List all backtest jobs" -> params with default values
            - Use when: "Show only completed backtests" -> params with status='completed'
            - Don't use when: You need to create a new backtest (use etf_arbitrage_run_backtest instead)
            - Don't use when: You need detailed results (use etf_arbitrage_get_backtest_result instead)

        Error Handling:
            - Returns empty list if no backtests found
            - Returns formatted list with pagination metadata
        """
        try:
            backend = get_backend()
            backtest_repo = backend.get_backtest_repository()

            # Fetch jobs
            jobs = backtest_repo.list_jobs(limit=params.limit + params.offset)
            total = len(jobs)

            # Apply pagination and filter
            paginated_jobs = jobs[params.offset:params.offset + params.limit]
            if params.status:
                paginated_jobs = [j for j in paginated_jobs if j.get('status') == params.status]

            # Convert to dict format
            job_dicts = []
            for job in paginated_jobs:
                job_dicts.append({
                    'job_id': job.get('job_id'),
                    'status': job.get('status'),
                    'start_date': job.get('config', {}).get('start_date'),
                    'end_date': job.get('config', {}).get('end_date'),
                    'total_signals': len(job.get('signals', [])),
                    'event_detector': job.get('config', {}).get('event_detector'),
                    'fund_selector': job.get('config', {}).get('fund_selector'),
                    'created_at': job.get('created_at'),
                    'completed_at': job.get('completed_at'),
                })

            # Build response
            if params.response_format == ResponseFormat.JSON:
                import json
                response = {
                    'jobs': job_dicts,
                    'pagination': {
                        'total': total,
                        'count': len(job_dicts),
                        'offset': params.offset,
                        'has_more': params.offset + len(job_dicts) < total,
                        'next_offset': params.offset + len(job_dicts) if params.offset + len(job_dicts) < total else None,
                    }
                }
                return json.dumps(response, indent=2, ensure_ascii=False, default=str)

            # Markdown format
            status_filter = f" (status: {params.status})" if params.status else ""

            lines = [
                f"# Backtest Jobs{status_filter}",
                "",
                f"Found {total} jobs (showing {len(job_dicts)})",
                "",
            ]

            status_emoji = {
                'pending': '⏳',
                'running': '🔄',
                'completed': '✅',
                'failed': '❌',
            }

            for job in job_dicts:
                emoji = status_emoji.get(job['status'], '❓')
                lines.append(f"## {job['job_id'][:8]} {emoji}")
                lines.append(f"- **Status**: {job['status'].upper()}")
                lines.append(f"- **Date Range**: {job['start_date']} to {job['end_date']}")
                lines.append(f"- **Signals**: {job['total_signals']}")
                lines.append(f"- **Strategy**: {job['event_detector']} / {job['fund_selector']}")
                lines.append(f"- **Created**: {format_timestamp(job['created_at'])}")
                lines.append("")

            # Add pagination info
            if params.offset + len(job_dicts) < total:
                lines.append(f"**Next page**: Use offset={params.offset + len(job_dicts)}")

            return "\n".join(lines)

        except Exception as e:
            return ToolResponse.error(f"Failed to list backtests: {str(e)}")


# ============================================================================
# Async Backtest Runner
# ============================================================================

async def _run_backtest_async(job_id: str, config: Dict[str, Any], backend) -> None:
    """Run backtest asynchronously in the background.

    Args:
        job_id: Backtest job ID
        config: Backtest configuration
        backend: Backend bridge instance
    """
    import logging
    logger = logging.getLogger(__name__)

    backtest_repo = backend.data.backtest_repository
    backtest_engine = backend.get_backtest_engine()

    try:
        # Update status to running
        await backtest_repo.update_status(job_id, 'running')

        # Run backtest
        results = await backtest_engine.run_backtest(
            start_date=config['start_date'],
            end_date=config['end_date'],
            event_detector=config['event_detector'],
            fund_selector=config['fund_selector'],
            signal_filters=config['signal_filters'],
            granularity=config.get('granularity', 'daily'),
        )

        # Update job with results
        await backtest_repo.complete_job(
            job_id=job_id,
            signals=results.get('signals', []),
            performance=results.get('performance', {}),
        )

        logger.info(f"Backtest {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Backtest {job_id} failed: {str(e)}")
        await backtest_repo.fail_job(
            job_id=job_id,
            error=str(e),
        )
