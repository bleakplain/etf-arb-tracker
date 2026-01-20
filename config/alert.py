"""
告警配置模块

定义消息通知渠道的配置
"""

from dataclasses import dataclass
from typing import List


@dataclass
class DingTalkSettings:
    """钉钉机器人设置"""

    enabled: bool = False
    webhook: str = ""
    secret: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "DingTalkSettings":
        """从字典创建配置"""
        return cls(
            enabled=data.get("enabled", False),
            webhook=data.get("webhook", ""),
            secret=data.get("secret", ""),
        )


@dataclass
class EmailSettings:
    """邮件通知设置"""

    enabled: bool = False
    smtp_server: str = "smtp.qq.com"
    smtp_port: int = 465
    sender: str = ""
    password: str = ""
    receivers: List[str] = None

    def __post_init__(self):
        if self.receivers is None:
            self.receivers = []

    @classmethod
    def from_dict(cls, data: dict) -> "EmailSettings":
        """从字典创建配置"""
        return cls(
            enabled=data.get("enabled", False),
            smtp_server=data.get("smtp_server", "smtp.qq.com"),
            smtp_port=data.get("smtp_port", 465),
            sender=data.get("sender", ""),
            password=data.get("password", ""),
            receivers=data.get("receivers", []),
        )


@dataclass
class WeChatWorkSettings:
    """企业微信设置"""

    enabled: bool = False
    webhook: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "WeChatWorkSettings":
        """从字典创建配置"""
        return cls(
            enabled=data.get("enabled", False),
            webhook=data.get("webhook", ""),
        )


@dataclass
class AlertSettings:
    """告警设置"""

    enabled: bool = True
    dingtalk: DingTalkSettings = None
    email: EmailSettings = None
    wechat_work: WeChatWorkSettings = None

    def __post_init__(self):
        if self.dingtalk is None:
            self.dingtalk = DingTalkSettings()
        if self.email is None:
            self.email = EmailSettings()
        if self.wechat_work is None:
            self.wechat_work = WeChatWorkSettings()

    @classmethod
    def from_dict(cls, data: dict) -> "AlertSettings":
        """从字典创建配置"""
        return cls(
            enabled=data.get("enabled", True),
            dingtalk=DingTalkSettings.from_dict(data.get("dingtalk", {})),
            email=EmailSettings.from_dict(data.get("email", {})),
            wechat_work=WeChatWorkSettings.from_dict(data.get("wechat_work", {})),
        )

    def has_enabled_channel(self) -> bool:
        """检查是否有启用的通知渠道"""
        return self.enabled and (
            self.dingtalk.enabled
            or self.email.enabled
            or self.wechat_work.enabled
        )
