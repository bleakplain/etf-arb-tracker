"""
Core infrastructure components

This module contains foundational infrastructure components
that support extensibility and plugin architecture.
"""

from .registry import PluginRegistry, evaluator_registry, sender_registry, source_registry
from .strategy_registry import (
    event_detector_registry,
    fund_selector_registry,
    signal_filter_registry,
    strategy_manager
)
from .plugin_manager import list_all_plugins, print_plugin_summary

__all__ = [
    # Plugin Registries
    'PluginRegistry',
    'evaluator_registry',
    'sender_registry',
    'source_registry',
    # Strategy Registries
    'event_detector_registry',
    'fund_selector_registry',
    'signal_filter_registry',
    'strategy_manager',
    # Plugin Management
    'list_all_plugins',
    'print_plugin_summary',
]
