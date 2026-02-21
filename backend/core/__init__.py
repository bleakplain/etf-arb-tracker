"""
Core infrastructure components

This module contains foundational infrastructure components
that support extensibility and plugin architecture.
"""

from .registry import PluginRegistry, evaluator_registry, sender_registry, source_registry

__all__ = [
    'PluginRegistry',
    'evaluator_registry',
    'sender_registry',
    'source_registry',
]
