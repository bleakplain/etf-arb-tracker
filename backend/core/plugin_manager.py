"""
插件管理工具

提供插件注册表的查询和管理功能
"""

from typing import Dict, List
from loguru import logger

from backend.core.registry import evaluator_registry, sender_registry, source_registry


def list_all_plugins() -> Dict[str, Dict]:
    """
    列出所有已注册的插件

    Returns:
        {
            "evaluators": {name: metadata},
            "senders": {name: metadata},
            "sources": {name: metadata}
        }
    """
    return {
        "evaluators": _get_registry_info(evaluator_registry),
        "senders": _get_registry_info(sender_registry),
        "sources": _get_registry_info(source_registry),
    }


def _get_registry_info(registry) -> Dict:
    """获取注册表信息"""
    info = {}
    for name in registry.list_names():
        info[name] = registry.get_metadata(name)
    return info


def print_plugin_summary():
    """打印插件摘要（用于调试）"""
    all_plugins = list_all_plugins()

    print("\n" + "=" * 60)
    print("插件注册表摘要")
    print("=" * 60)

    for registry_name, plugins in all_plugins.items():
        print(f"\n{registry_name.upper()} ({len(plugins)} 个插件):")
        for name, meta in plugins.items():
            print(f"  - {name}")
            print(f"    类: {meta.get('class_name', 'Unknown')}")
            print(f"    版本: {meta.get('version', '?')}")
            print(f"    优先级: {meta.get('priority', 0)}")
            if meta.get('description'):
                print(f"    描述: {meta.get('description')}")

    print("\n" + "=" * 60)


def get_plugin_stats() -> Dict:
    """
    获取插件统计信息

    Returns:
        {
            "total": 总插件数,
            "by_registry": 各注册表的插件数
        }
    """
    all_plugins = list_all_plugins()
    total = sum(len(plugins) for plugins in all_plugins.values())

    return {
        "total": total,
        "by_registry": {
            name: len(plugins) for name, plugins in all_plugins.items()
        }
    }


def validate_registries() -> bool:
    """
    验证所有注册表是否有效

    检查：
    - 每个注册表至少有一个插件
    - 所有插件都有必需的元数据

    Returns:
        是否验证通过
    """
    all_valid = True
    all_plugins = list_all_plugins()

    for registry_name, plugins in all_plugins.items():
        if not plugins:
            logger.warning(f"注册表 '{registry_name}' 没有注册任何插件")
            all_valid = False
            continue

        for name, meta in plugins.items():
            if not meta.get('class_name'):
                logger.warning(f"插件 '{registry_name}.{name}' 缺少 class_name 元数据")
                all_valid = False

            if not meta.get('version'):
                logger.warning(f"插件 '{registry_name}.{name}' 缺少 version 元数据")

    return all_valid


# 注册表快捷访问
def get_evaluator(name: str):
    """获取评估器类"""
    return evaluator_registry.get(name)


def get_sender(name: str):
    """获取发送器类"""
    return sender_registry.get(name)


def get_source(name: str):
    """获取数据源类"""
    return source_registry.get(name)


def create_evaluator(name: str, *args, **kwargs):
    """创建评估器实例"""
    return evaluator_registry.create(name, *args, **kwargs)


def create_sender(name: str, *args, **kwargs):
    """创建发送器实例"""
    return sender_registry.create(name, *args, **kwargs)


def create_source(name: str, *args, **kwargs):
    """创建数据源实例"""
    return source_registry.create(name, *args, **kwargs)
