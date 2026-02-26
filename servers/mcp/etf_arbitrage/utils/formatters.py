"""
Response formatting utilities for ETF Arbitrage MCP Server.

Handles conversion between internal data structures and formatted output
(JSON or Markdown).
"""

import json
from typing import Any, List, Dict, Optional
from datetime import datetime


class ResponseFormatter:
    """Base formatter for converting data to different output formats."""

    @staticmethod
    def to_json(data: Any, indent: int = 2) -> str:
        """Convert data to JSON string.

        Args:
            data: Data to convert
            indent: JSON indentation level

        Returns:
            str: JSON-formatted string
        """
        if isinstance(data, str):
            return data
        return json.dumps(data, indent=indent, ensure_ascii=False, default=str)

    @staticmethod
    def to_markdown(content: str) -> str:
        """Return content as-is (already markdown).

        Args:
            content: Markdown content

        Returns:
            str: Same content
        """
        return content


class StockFormatter:
    """Formatter for stock-related responses."""

    @staticmethod
    def format_quote(quote: Dict[str, Any], format_type: str) -> str:
        """Format a single stock quote.

        Args:
            quote: Stock quote data
            format_type: 'json' or 'markdown'

        Returns:
            str: Formatted quote
        """
        if format_type == "json":
            return json.dumps(quote, indent=2, ensure_ascii=False, default=str)

        # Markdown format
        lines = [
            f"## {quote.get('name', 'N/A')} ({quote.get('code', 'N/A')})",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| **Price** | {quote.get('price', 0):.2f} |",
            f"| **Change** | {quote.get('change', 0):+.2f} ({quote.get('change_pct', 0):+.2f}%) |",
            f"| **Volume** | {quote.get('volume', 0):,} |",
            f"| **Amount** | {quote.get('amount', 0):,.2f} |",
            f"| **High/Low** | {quote.get('high', 0):.2f} / {quote.get('low', 0):.2f} |",
            f"| **Market** | {quote.get('market', 'N/A').upper()} |",
        ]

        if quote.get('is_limit_up'):
            lines.append("| **Status** | 🔴 涨停 |")
        elif quote.get('is_limit_down'):
            lines.append("| **Status** | 🟢 跌停 |")

        return "\n".join(lines)

    @staticmethod
    def format_quotes(quotes: List[Dict[str, Any]], format_type: str) -> str:
        """Format multiple stock quotes.

        Args:
            quotes: List of stock quotes
            format_type: 'json' or 'markdown'

        Returns:
            str: Formatted quotes
        """
        if format_type == "json":
            return json.dumps(quotes, indent=2, ensure_ascii=False, default=str)

        # Markdown format
        if not quotes:
            return "# Stock Quotes\n\nNo quotes found."

        lines = ["# Stock Quotes", "", f"Found {len(quotes)} stocks", ""]

        for quote in quotes:
            lines.append(f"## {quote.get('name', 'N/A')} ({quote.get('code', 'N/A')})")
            lines.append(f"- **Price**: {quote.get('price', 0):.2f}")
            lines.append(f"- **Change**: {quote.get('change', 0):+.2f} ({quote.get('change_pct', 0):+.2f}%)")
            lines.append(f"- **Volume**: {quote.get('volume', 0):,}")

            if quote.get('is_limit_up'):
                lines.append("- **Status**: 🔴 涨停")

            lines.append("")

        return "\n".join(lines)


class ETFFormatter:
    """Formatter for ETF-related responses."""

    @staticmethod
    def format_related_etf(etf: Dict[str, Any], format_type: str) -> str:
        """Format a related ETF entry.

        Args:
            etf: ETF data with weight information
            format_type: 'json' or 'markdown'

        Returns:
            str: Formatted ETF info
        """
        if format_type == "json":
            return json.dumps(etf, indent=2, ensure_ascii=False, default=str)

        weight_pct = etf.get('weight_pct', etf.get('weight', 0) * 100)
        lines = [
            f"### {etf.get('name', 'N/A')} ({etf.get('code', 'N/A')})",
            f"- **Weight**: {weight_pct:.2f}%",
            f"- **Market**: {etf.get('market', 'N/A').upper()}",
        ]

        if etf.get('category'):
            lines.append(f"- **Category**: {etf['category']}")

        if etf.get('premium_rate') is not None:
            lines.append(f"- **Premium Rate**: {etf['premium_rate']:+.2f}%")

        if etf.get('daily_amount'):
            lines.append(f"- **Daily Amount**: {etf['daily_amount']:,.2f}")

        return "\n".join(lines)


class SignalFormatter:
    """Formatter for signal-related responses."""

    @staticmethod
    def format_signal(signal: Dict[str, Any], format_type: str) -> str:
        """Format a single signal.

        Args:
            signal: Signal data
            format_type: 'json' or 'markdown'

        Returns:
            str: Formatted signal
        """
        if format_type == "json":
            return json.dumps(signal, indent=2, ensure_ascii=False, default=str)

        timestamp = signal.get('timestamp', signal.get('created_at', 'N/A'))
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        elif isinstance(timestamp, str) and len(timestamp) > 19:
            timestamp = timestamp[:19]

        lines = [
            f"## Signal {signal.get('id', 'N/A')[:8]}",
            "",
            f"- **Stock**: {signal.get('stock_name', 'N/A')} ({signal.get('stock_code', 'N/A')})",
            f"- **ETF**: {signal.get('etf_name', 'N/A')} ({signal.get('etf_code', 'N/A')})",
            f"- **Weight**: {signal.get('weight', 0)*100:.2f}%",
            f"- **Event**: {signal.get('event_type', 'N/A')}",
            f"- **Confidence**: {signal.get('confidence', 0)*100:.1f}%",
            f"- **Time**: {timestamp}",
        ]

        return "\n".join(lines)


class PaginationFormatter:
    """Formatter for paginated responses."""

    @staticmethod
    def format_pagination(data: Dict[str, Any], format_type: str) -> str:
        """Format paginated response metadata.

        Args:
            data: Pagination data (total, count, offset, has_more, next_offset)
            format_type: 'json' or 'markdown'

        Returns:
            str: Formatted pagination info
        """
        if format_type == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)

        lines = [
            "---",
            f"**Pagination**: Showing {data.get('count', 0)} of {data.get('total', 0)} items",
        ]

        if data.get('has_more'):
            next_offset = data.get('next_offset', data.get('offset', 0) + data.get('count', 0))
            lines.append(f"**Next page**: Use offset={next_offset}")

        return " ".join(lines)


def format_timestamp(ts: Any) -> str:
    """Format a timestamp to human-readable string.

    Args:
        ts: Timestamp (datetime, str, or int)

    Returns:
        str: Formatted timestamp
    """
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(ts, str):
        # Try parsing common formats
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return ts[:19] if len(ts) >= 19 else ts
    elif isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(ts)


def format_number(num: Any, decimals: int = 2) -> str:
    """Format a number with thousand separators.

    Args:
        num: Number to format
        decimals: Number of decimal places

    Returns:
        str: Formatted number
    """
    try:
        n = float(num)
        return f"{n:,.{decimals}f}"
    except (ValueError, TypeError):
        return str(num)
