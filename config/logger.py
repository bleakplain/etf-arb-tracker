"""
日志配置模块

提供结构化日志配置，支持：
- JSON格式输出到文件
- 彩色格式输出到控制台
- 日志轮转和归档
- 错误日志分离
"""

import sys
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from loguru import logger
from datetime import datetime


@dataclass
class LoggerSettings:
    """日志设置"""

    level: str = "INFO"
    file: str = "logs/app.log"
    rotation: str = "100 MB"
    retention: str = "30 days"
    console_output: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "LoggerSettings":
        """从字典创建配置"""
        return cls(
            level=data.get("level", "INFO"),
            file=data.get("file", "logs/app.log"),
            rotation=data.get("rotation", "100 MB"),
            retention=data.get("retention", "30 days"),
            console_output=data.get("console_output", True),
        )


class LoggerManager:
    """日志管理器"""

    def __init__(self, settings: LoggerSettings):
        self.settings = settings
        self.log_dir = Path(settings.file).parent
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _serialize(self, record: dict) -> str:
        """将日志记录序列化为JSON格式"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record["time"].timestamp()).isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "module": record["module"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        }

        if record["exception"]:
            log_entry["exception"] = {
                "type": record["exception"].type.__name__ if record["exception"].type else None,
                "value": str(record["exception"].value) if record["exception"].value else None,
                "traceback": record["exception"].traceback if record["exception"].traceback else None,
            }

        extra = record.get("extra", {})
        if extra:
            for key, value in extra.items():
                if key not in ["serial"]:
                    log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)

    def _console_format(self, record: dict) -> str:
        """控制台输出格式 - 彩色且易读"""
        level = record["level"]
        time_str = datetime.fromtimestamp(record["time"].timestamp()).strftime("%H:%M:%S")

        level_color = {
            "TRACE": "<dim>",
            "DEBUG": "<cyan>",
            "INFO": "<green>",
            "SUCCESS": "<green><bold>",
            "WARNING": "<yellow>",
            "ERROR": "<red>",
            "CRITICAL": "<RED><bold>",
        }.get(level.name, "")

        level_reset = "</>" if level_color else ""

        return (
            f"<dim>{time_str}</dim> | "
            f"{level_color}{level.name:8}{level_reset} | "
            f"<cyan>{record['name']:20}</cyan> | "
            f"<dim>{record['function']}:{record['line']}</dim> | "
            f"{record['message']}\n"
        )

    def setup(self):
        """配置日志系统"""
        logger.remove()

        if self.settings.console_output:
            logger.add(
                sys.stderr,
                format=self._console_format,
                level=self.settings.level,
                colorize=True,
                enqueue=True,
                catch=True,
            )

        # 文件输出 - 使用 serialize=True 自动序列化
        logger.add(
            self.settings.file,
            format="{message}",
            level="DEBUG",
            rotation=self.settings.rotation,
            retention=self.settings.retention,
            enqueue=True,
            serialize=True,
            encoding="utf-8",
            catch=True,
        )

        # 错误日志单独文件
        error_file = self.settings.file.replace(".log", "_error.log")
        logger.add(
            error_file,
            format="{message}",
            level="ERROR",
            rotation=self.settings.rotation,
            retention=self.settings.retention,
            enqueue=True,
            serialize=True,
            encoding="utf-8",
            catch=True,
        )


def setup(settings: Optional[LoggerSettings] = None) -> LoggerManager:
    """
    设置日志系统

    Args:
        settings: 日志设置，默认使用默认设置

    Returns:
        LoggerManager: 日志管理器实例
    """
    if settings is None:
        settings = LoggerSettings()

    manager = LoggerManager(settings)
    manager.setup()
    return manager
