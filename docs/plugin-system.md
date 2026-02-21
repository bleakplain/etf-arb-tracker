# Plugin System Guide

## Overview

The ETF Arbitrage Tracker now supports a **plugin registry system** that allows you to extend the system without modifying core factory code. Plugins can self-register using decorators.

## Architecture

```
backend/core/
├── __init__.py           # Core exports
├── registry.py           # PluginRegistry class and global registries
└── plugin_manager.py     # Plugin management utilities
```

## Supported Plugin Types

| Registry | Base Class | Purpose |
|----------|-----------|---------|
| `evaluator_registry` | `SignalEvaluator` | Signal evaluation strategies |
| `sender_registry` | `NotificationSender` | Notification channels |
| `source_registry` | `BaseDataSource` | Data sources |

## Creating Custom Plugins

### 1. Signal Evaluator Plugin

Create a new evaluator in `backend/strategy/custom_evaluators.py`:

```python
from backend.strategy.signal_evaluators import SignalEvaluator
from backend.core.registry import evaluator_registry
from typing import Dict, Tuple

@evaluator_registry.register(
    "my_custom",
    priority=50,
    description="My custom evaluation strategy",
    version="1.0.0"
)
class MyCustomEvaluator(SignalEvaluator):
    """自定义信号评估器"""

    def evaluate(self, limit_info: Dict, etf_info: Dict) -> Tuple[str, str]:
        # 实现自定义评估逻辑
        weight = etf_info.get('weight', 0)

        if weight > 0.10:
            return "高", "低"
        elif weight > 0.05:
            return "中", "中"
        else:
            return "低", "高"
```

Then use it in config:
```yaml
signal_evaluation:
  evaluator_type: "my_custom"  # Uses your custom evaluator
```

### 2. Notification Sender Plugin

Create a new sender in `backend/notification/custom_senders.py`:

```python
from backend.notification.sender import NotificationSender
from backend.core.registry import sender_registry
from backend.domain.value_objects import TradingSignal

@sender_registry.register(
    "slack",
    priority=50,
    description="Slack notification channel",
    version="1.0.0"
)
class SlackSender(NotificationSender):
    """Slack通知发送器"""

    def __init__(self, webhook: str, channel: str = "#alerts"):
        self.webhook = webhook
        self.channel = channel

    def send_signal(self, signal: TradingSignal) -> bool:
        # 实现Slack发送逻辑
        import requests

        message = {
            "channel": self.channel,
            "text": f"Signal: {signal.stock_name} -> {signal.etf_name}"
        }

        try:
            response = requests.post(self.webhook, json=message, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False
```

Configure in `settings.yaml`:
```yaml
notification:
  slack:
    enabled: true
    webhook: "https://hooks.slack.com/services/YOUR/WEBHOOK"
    channel: "#trading-alerts"
```

Add configuration class in `config/alert.py`:
```python
@dataclass
class SlackSettings:
    """Slack通知设置"""
    enabled: bool = False
    webhook: str = ""
    channel: str = "#alerts"
```

### 3. Data Source Plugin

Create a new data source in `backend/data/sources/custom_source.py`:

```python
from backend.data.source_base import BaseDataSource
from backend.core.registry import source_registry
import pandas as pd

@source_registry.register(
    "my_provider",
    priority=75,
    description="My custom data provider",
    version="1.0.0"
)
class MyCustomSource(BaseDataSource):
    """自定义数据源"""

    def __init__(self, priority: int = 1, api_key: str = ""):
        super().__init__("my_provider", SourceType.PAID_LOW_FREQ, priority)
        self.api_key = api_key

    def _get_capability(self):
        return SourceCapability(
            supported_types={DataType.STOCK_REALTIME, DataType.ETF_REALTIME},
            realtime=True,
            historical=False,
            batch_query=True,
            max_batch_size=50,
            requires_token=True,
            rate_limit=100  # 100 requests per minute
        )

    def _check_config(self):
        return bool(self.api_key)

    def fetch_stock_spot(self, stock_codes=None):
        # 实现数据获取逻辑
        pass
```

## API Endpoints

### List All Plugins

```bash
GET /api/plugins
```

Response:
```json
{
  "evaluators": {
    "default": {
      "class_name": "DefaultSignalEvaluator",
      "version": "1.0.0",
      "priority": 100,
      "description": "默认信号评估器"
    },
    "conservative": {...}
  },
  "senders": {
    "dingtalk": {...},
    "email": {...}
  },
  "sources": {
    "tencent": {...}
  }
}
```

### Get Plugin Statistics

```bash
GET /api/plugins/stats
```

Response:
```json
{
  "total": 8,
  "by_registry": {
    "evaluators": 3,
    "senders": 3,
    "sources": 2
  }
}
```

## Plugin Metadata

When registering a plugin, you can specify:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | Yes | Unique plugin identifier |
| `priority` | int | No | Order preference (higher = preferred) |
| `description` | str | No | Human-readable description |
| `version` | str | No | Plugin version (default: "1.0.0") |

## Registry Methods

### Checking Registration

```python
from backend.core.registry import evaluator_registry

if evaluator_registry.is_registered("my_custom"):
    # Plugin exists
    evaluator_cls = evaluator_registry.get("my_custom")
```

### Creating Plugin Instances

```python
from backend.core.plugin_manager import create_evaluator

evaluator = create_evaluator("my_custom", config=my_config)
```

### Listing Available Plugins

```python
from backend.core.registry import evaluator_registry

names = evaluator_registry.list_names()  # Sorted by priority
all_plugins = evaluator_registry.list_all()  # {name: class}
```

## Best Practices

1. **Use descriptive names**: `my_custom_evaluator` → `momentum_rsi`
2. **Set appropriate priority**: Higher priority plugins are preferred
3. **Provide version**: Track changes with semantic versioning
4. **Add descriptions**: Help users understand what your plugin does
5. **Handle errors gracefully**: Return sensible defaults on failure
6. **Log important events**: Use `logger` for debugging
7. **Document configuration**: Clearly explain required config parameters

## Migration from Old System

### Before (Hardcoded Factory)

```python
class SignalEvaluatorFactory:
    @staticmethod
    def create(type: str):
        evaluators = {
            "default": DefaultSignalEvaluator,
            "custom": MyCustomEvaluator  # Had to add here
        }
        return evaluators[type](config)
```

### After (Plugin Registry)

```python
# No factory modification needed!
# Just register your class:

@evaluator_registry.register("custom")
class MyCustomEvaluator(SignalEvaluator):
    ...

# Factory automatically discovers it:
evaluator = SignalEvaluatorFactory.create("custom")
```

## Troubleshooting

### Plugin Not Found

```python
ValueError: 未知的评估器类型: 'my_custom'
```

**Solution**:
1. Check plugin is imported: Make sure the module defining the plugin is imported
2. Check name matches: Use exact name from `@evaluator_registry.register("name")`
3. List available: Call `/api/plugins` to see registered plugins

### Configuration Not Found

```python
AttributeError: 'AlertSettings' object has no attribute 'slack'
```

**Solution**:
1. Add settings class to `config/alert.py`
2. Add field to `AlertSettings` dataclass
3. Add mapping in `create_sender_from_config()`

### Registration Overwritten

If you register two plugins with the same name, the second one replaces the first:

```python
@evaluator_registry.register("custom")
class FirstEvaluator(SignalEvaluator):
    pass

@evaluator_registry.register("custom")  # Overwrites FirstEvaluator!
class SecondEvaluator(SignalEvaluator):
    pass
```

**Solution**: Use unique names for each plugin.

## Examples

See these files for complete examples:
- `backend/strategy/signal_evaluators.py` - Signal evaluators
- `backend/notification/sender.py` - Notification senders
- `backend/data/sources/tencent_source.py` - Data sources
