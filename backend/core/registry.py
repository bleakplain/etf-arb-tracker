"""
Plugin Registry System

Provides a generic plugin registry for extensible components.
Allows plugins to self-register via decorators, eliminating the need
to modify factory code when adding new extensions.

Usage:
    @evaluator_registry.register("default")
    class MyEvaluator(BaseEvaluator):
        pass

    # Later:
    evaluator_cls = evaluator_registry.get("default")
    evaluator = evaluator_cls(config)
"""

from typing import Dict, Type, TypeVar, Callable, Optional, List, Any
from loguru import logger

T = TypeVar('T')


class PluginRegistry:
    """
    Generic plugin registry for extensible components.

    Supports:
    - Decorator-based registration
    - Manual registration
    - Plugin lookup by name
    - Listing all registered plugins
    - Validation of plugin base classes
    """

    def __init__(self, registry_name: str, base_class: Optional[Type] = None):
        """
        Initialize the plugin registry.

        Args:
            registry_name: Name of this registry (for logging)
            base_class: Optional base class that all plugins must inherit from
        """
        self._name = registry_name
        self._base_class = base_class
        self._plugins: Dict[str, Type[T]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        *,
        priority: int = 0,
        description: str = "",
        version: str = "1.0.0"
    ) -> Callable[[Type[T]], Type[T]]:
        """
        Decorator for plugin registration.

        Args:
            name: Unique name for this plugin
            priority: Priority for ordering (higher = preferred)
            description: Human-readable description
            version: Plugin version

        Returns:
            Decorator function

        Example:
            @evaluator_registry.register("conservative", priority=10)
            class ConservativeEvaluator(BaseEvaluator):
                pass
        """
        def decorator(cls: Type[T]) -> Type[T]:
            # Validate base class if specified
            if self._base_class is not None:
                if not isinstance(cls, type):
                    raise TypeError(f"Plugin {name} must be a class")
                # Check if cls is a subclass of base_class (but not the base itself)
                try:
                    if not (issubclass(cls, self._base_class) and cls is not self._base_class):
                        raise TypeError(
                            f"Plugin {name} must inherit from {self._base_class.__name__}"
                        )
                except TypeError as e:
                    # Not a class or inheritance check failed
                    raise TypeError(
                        f"Plugin {name} must be a class inheriting from {self._base_class.__name__}: {e}"
                    )

            # Register the plugin
            if name in self._plugins:
                existing = self._plugins[name]
                logger.warning(
                    f"[{self._name}] Plugin '{name}' already registered "
                    f"(replacing {existing.__name__} with {cls.__name__})"
                )

            self._plugins[name] = cls
            self._metadata[name] = {
                'priority': priority,
                'description': description,
                'version': version,
                'class_name': cls.__name__,
                'module': cls.__module__
            }

            logger.debug(
                f"[{self._name}] Registered plugin '{name}': {cls.__name__} "
                f"(v{version}, priority={priority})"
            )

            return cls

        return decorator

    def register_manual(
        self,
        name: str,
        cls: Type[T],
        *,
        priority: int = 0,
        description: str = "",
        version: str = "1.0.0"
    ) -> None:
        """
        Manually register a plugin (without decorator).

        Args:
            name: Unique name for this plugin
            cls: Plugin class to register
            priority: Priority for ordering
            description: Human-readable description
            version: Plugin version
        """
        decorator = self.register(name, priority=priority, description=description, version=version)
        decorator(cls)

    def get(self, name: str, default: Optional[T] = None) -> Optional[Type[T]]:
        """
        Get plugin class by name.

        Args:
            name: Plugin name
            default: Default value if not found

        Returns:
            Plugin class or default
        """
        return self._plugins.get(name, default)

    def create(self, name: str, *args, **kwargs) -> Optional[T]:
        """
        Create a plugin instance by name.

        Args:
            name: Plugin name
            *args: Positional args to pass to plugin constructor
            **kwargs: Keyword args to pass to plugin constructor

        Returns:
            Plugin instance or None if not found
        """
        cls = self.get(name)
        if cls is None:
            logger.warning(f"[{self._name}] Plugin '{name}' not found")
            return None
        return cls(*args, **kwargs)

    def list_all(self) -> Dict[str, Type[T]]:
        """
        List all registered plugins.

        Returns:
            Dictionary mapping name to plugin class
        """
        return self._plugins.copy()

    def list_names(self) -> List[str]:
        """
        List all registered plugin names.

        Returns:
            List of plugin names sorted by priority (descending)
        """
        names = list(self._plugins.keys())
        # Sort by priority (descending)
        names.sort(key=lambda n: self._metadata.get(n, {}).get('priority', 0), reverse=True)
        return names

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """
        Get plugin metadata.

        Args:
            name: Plugin name

        Returns:
            Metadata dictionary or empty dict if not found
        """
        return self._metadata.get(name, {}).copy()

    def is_registered(self, name: str) -> bool:
        """
        Check if a plugin is registered.

        Args:
            name: Plugin name

        Returns:
            True if registered
        """
        return name in self._plugins

    def unregister(self, name: str) -> bool:
        """
        Unregister a plugin.

        Args:
            name: Plugin name

        Returns:
            True if unregistered, False if not found
        """
        if name in self._plugins:
            del self._plugins[name]
            del self._metadata[name]
            logger.debug(f"[{self._name}] Unregistered plugin '{name}'")
            return True
        return False

    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
        self._metadata.clear()
        logger.debug(f"[{self._name}] Cleared all plugins")

    def count(self) -> int:
        """Get the number of registered plugins."""
        return len(self._plugins)

    def summary(self) -> str:
        """
        Get a summary of all registered plugins.

        Returns:
            Formatted summary string
        """
        lines = [f"Plugin Registry: {self._name}", f"Total plugins: {self.count()}"]
        for name in self.list_names():
            meta = self._metadata.get(name, {})
            lines.append(
                f"  - {name}: {meta.get('class_name', 'Unknown')} "
                f"(v{meta.get('version', '?')}, priority={meta.get('priority', 0)})"
            )
        return "\n".join(lines)


# =============================================================================
# Global Registry Instances
# =============================================================================

# Signal evaluator registry
evaluator_registry = PluginRegistry(
    "SignalEvaluator",
    base_class=None  # Will be set after BaseEvaluator is defined
)

# Notification sender registry
sender_registry = PluginRegistry(
    "NotificationSender",
    base_class=None  # Will be set after NotificationSender is defined
)

# Data source registry
source_registry = PluginRegistry(
    "DataSource",
    base_class=None  # Will be set after BaseDataSource is defined
)
