"""
告警配置模块

定义消息通知的配置
"""

from dataclasses import dataclass


@dataclass
class AlertSettings:
    """告警设置"""

    enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "AlertSettings":
        """从字典创建配置"""
        return cls(
            enabled=data.get("enabled", True),
        )

    def has_enabled_channel(self) -> bool:
        """检查是否有启用的通知渠道"""
        return self.enabled
