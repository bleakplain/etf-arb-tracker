"""
消息通知模块
支持钉钉、邮件、企业微信等多种通知方式
"""

import hmac
import hashlib
import base64
import urllib.parse
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import requests
from loguru import logger

from backend.strategy.limit_monitor import TradingSignal
from config import Config


class NotificationSender:
    """消息通知发送器基类"""

    def send_signal(self, signal: TradingSignal):
        """发送信号通知"""
        raise NotImplementedError


class DingTalkSender(NotificationSender):
    """钉钉机器人通知"""

    def __init__(self, webhook: str, secret: str = ""):
        """
        初始化钉钉机器人

        Args:
            webhook: 钉钉机器人Webhook地址
            secret: 安全设置-加签的密钥（可选）
        """
        self.webhook = webhook
        self.secret = secret

    def _generate_sign(self, timestamp: int) -> str:
        """生成签名"""
        if not self.secret:
            return ""

        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')

        hmac_code = hmac.new(secret_enc, string_to_sign_enc,
                            digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

        return sign

    def _build_message(self, signal: TradingSignal) -> dict:
        """构建钉钉消息"""
        # 根据风险等级选择emoji
        risk_emoji = {
            "高": "🔴",
            "中": "🟡",
            "低": "🟢"
        }
        confidence_emoji = {
            "高": "💪",
            "中": "👍",
            "低": "⚠️"
        }

        title = f"📈 涨停ETF套利信号 - {signal.stock_name}"

        text = f"""### {title}

**⏰ 时间**: {signal.timestamp}

**🔴 涨停股票**
> 代码: {signal.stock_code}
> 名称: {signal.stock_name}
> 价格: ¥{signal.stock_price:.2f}
> 封单: ¥{signal.seal_amount/100000000:.2f}亿

**💰 建议买入ETF**
> 代码: {signal.etf_code}
> 名称: {signal.etf_name}
> 当前价: ¥{signal.etf_price:.3f}
> 权重: {signal.etf_weight*100:.2f}%
> 溢价: {signal.etf_premium:+.2f}%

**📊 信号评估**
> 置信度: {confidence_emoji.get(signal.confidence, '')} {signal.confidence}
> 风险: {risk_emoji.get(signal.risk_level, '')} {signal.risk_level}

**💡 说明**: {signal.reason}

---
⚠️ 风险提示: 本信号仅供参考，不构成投资建议。请根据自身情况谨慎决策。
"""

        return {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text
            }
        }

    def send_signal(self, signal: TradingSignal):
        """发送信号到钉钉"""
        if not self.webhook:
            logger.warning("钉钉Webhook未配置，跳过发送")
            return False

        try:
            # 构建URL
            timestamp = int(time.time() * 1000)
            url = self.webhook

            if self.secret:
                sign = self._generate_sign(timestamp)
                url = f"{self.webhook}&timestamp={timestamp}&sign={sign}"

            # 构建消息
            message = self._build_message(signal)

            # 发送
            response = requests.post(url, json=message, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.success(f"钉钉通知发送成功: {signal.stock_name}")
                    return True
                else:
                    logger.error(f"钉钉通知失败: {result}")
                    return False
            else:
                logger.error(f"钉钉通知请求失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"发送钉钉通知异常: {e}")
            return False


class EmailSender(NotificationSender):
    """邮件通知"""

    def __init__(self, smtp_server: str, smtp_port: int,
                 sender: str, password: str, receivers: List[str]):
        """
        初始化邮件发送器

        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            sender: 发件人邮箱
            password: 邮箱密码/授权码
            receivers: 收件人邮箱列表
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender
        self.password = password
        self.receivers = receivers

    def _build_message(self, signal: TradingSignal) -> MIMEMultipart:
        """构建邮件消息"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📈 涨停ETF套利信号 - {signal.stock_name}"
        msg['From'] = self.sender
        msg['To'] = ', '.join(self.receivers)

        # HTML内容
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background: #f0f0f0; padding: 10px; }}
                .section {{ margin: 15px 0; }}
                .stock {{ background: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; }}
                .etf {{ background: #d1ecf1; padding: 10px; border-left: 4px solid #17a2b8; }}
                .eval {{ background: #f8f9fa; padding: 10px; border-left: 4px solid #6c757d; }}
                table {{ border-collapse: collapse; width: 100%; }}
                td {{ padding: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📈 涨停ETF套利信号</h2>
                <p><strong>时间:</strong> {signal.timestamp}</p>
            </div>

            <div class="section stock">
                <h3>🔴 涨停股票</h3>
                <table>
                    <tr><td><strong>代码</strong></td><td>{signal.stock_code}</td></tr>
                    <tr><td><strong>名称</strong></td><td>{signal.stock_name}</td></tr>
                    <tr><td><strong>价格</strong></td><td>¥{signal.stock_price:.2f}</td></tr>
                </table>
            </div>

            <div class="section etf">
                <h3>💰 建议买入ETF</h3>
                <table>
                    <tr><td><strong>代码</strong></td><td>{signal.etf_code}</td></tr>
                    <tr><td><strong>名称</strong></td><td>{signal.etf_name}</td></tr>
                    <tr><td><strong>当前价</strong></td><td>¥{signal.etf_price:.3f}</td></tr>
                    <tr><td><strong>权重</strong></td><td>{signal.etf_weight*100:.2f}%</td></tr>
                    <tr><td><strong>溢价率</strong></td><td>{signal.etf_premium:+.2f}%</td></tr>
                </table>
            </div>

            <div class="section eval">
                <h3>📊 信号评估</h3>
                <p><strong>置信度:</strong> {signal.confidence}</p>
                <p><strong>风险等级:</strong> {signal.risk_level}</p>
                <p><strong>说明:</strong> {signal.reason}</p>
            </div>

            <hr>
            <p style="color: #999; font-size: 12px;">
                ⚠️ 风险提示: 本信号仅供参考，不构成投资建议。请根据自身情况谨慎决策。
            </p>
        </body>
        </html>
        """

        html_part = MIMEText(html, 'html', 'utf-8')
        msg.attach(html_part)

        return msg

    def send_signal(self, signal: TradingSignal):
        """发送邮件"""
        if not self.receivers:
            logger.warning("邮件收件人未配置，跳过发送")
            return False

        try:
            msg = self._build_message(signal)

            # 连接SMTP服务器
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()

            # 登录
            server.login(self.sender, self.password)

            # 发送
            server.send_message(msg)
            server.quit()

            logger.success(f"邮件通知发送成功: {signal.stock_name}")
            return True

        except Exception as e:
            logger.error(f"发送邮件通知异常: {e}")
            return False


class WeChatWorkSender(NotificationSender):
    """企业微信机器人通知"""

    def __init__(self, webhook: str):
        """
        初始化企业微信机器人

        Args:
            webhook: 企业微信机器人Webhook地址
        """
        self.webhook = webhook

    def _build_message(self, signal: TradingSignal) -> dict:
        """构建企业微信消息"""
        markdown = f"""
## 📈 涨停ETF套利信号

**时间**: {signal.timestamp}

### 🔴 涨停股票
> 代码: {signal.stock_code}
> 名称: {signal.stock_name}
> 价格: ¥{signal.stock_price:.2f}

### 💰 建议买入ETF
> 代码: {signal.etf_code}
> 名称: {signal.etf_name}
> 当前价: ¥{signal.etf_price:.3f}
> 权重: {signal.etf_weight*100:.2f}%
> 溢价: {signal.etf_premium:+.2f}%

### 📊 信号评估
> 置信度: {signal.confidence}
> 风险: {signal.risk_level}

> {signal.reason}

---
⚠️ 仅供参考，不构成投资建议
        """

        return {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown
            }
        }

    def send_signal(self, signal: TradingSignal):
        """发送到企业微信"""
        if not self.webhook:
            logger.warning("企业微信Webhook未配置，跳过发送")
            return False

        try:
            message = self._build_message(signal)
            response = requests.post(self.webhook, json=message, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logger.success(f"企业微信通知发送成功: {signal.stock_name}")
                    return True
                else:
                    logger.error(f"企业微信通知失败: {result}")
                    return False
            else:
                logger.error(f"企业微信通知请求失败: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"发送企业微信通知异常: {e}")
            return False


class MultiChannelSender(NotificationSender):
    """多渠道通知发送器"""

    def __init__(self):
        """初始化多渠道发送器"""
        self.senders: List[NotificationSender] = []

    def add_sender(self, sender: NotificationSender):
        """添加发送器"""
        self.senders.append(sender)

    def send_signal(self, signal: TradingSignal):
        """通过所有渠道发送信号"""
        success_count = 0

        for sender in self.senders:
            try:
                if sender.send_signal(signal):
                    success_count += 1
            except Exception as e:
                logger.error(f"发送失败: {e}")

        logger.info(f"信号发送完成: {success_count}/{len(self.senders)} 渠道成功")
        return success_count > 0


def create_sender_from_config(config) -> MultiChannelSender:
    """
    根据配置创建发送器

    Args:
        config: 应用配置

    Returns:
        多渠道发送器
    """
    sender = MultiChannelSender()

    # 钉钉
    if config.alert.dingtalk.enabled:
        dingtalk_sender = DingTalkSender(
            webhook=config.alert.dingtalk.webhook,
            secret=config.alert.dingtalk.secret
        )
        sender.add_sender(dingtalk_sender)

    # 邮件
    if config.alert.email.enabled:
        email_sender = EmailSender(
            smtp_server=config.alert.email.smtp_server,
            smtp_port=config.alert.email.smtp_port,
            sender=config.alert.email.sender,
            password=config.alert.email.password,
            receivers=config.alert.email.receivers
        )
        sender.add_sender(email_sender)

    # 企业微信
    if config.alert.wechat_work.enabled:
        wechat_sender = WeChatWorkSender(
            webhook=config.alert.wechat_work.webhook
        )
        sender.add_sender(wechat_sender)

    return sender


# 测试代码
if __name__ == "__main__":
    from backend.strategy.limit_monitor import TradingSignal

    # 创建测试信号
    test_signal = TradingSignal(
        signal_id="TEST_001",
        timestamp="2025-01-09 14:35:00",
        stock_code="300750",
        stock_name="宁德时代",
        stock_price=256.80,
        limit_time="14:35:00",
        seal_amount=1500000000,
        etf_code="516160",
        etf_name="新能源车ETF",
        etf_weight=0.085,
        etf_price=1.234,
        etf_premium=2.5,
        reason="宁德时代涨停，在新能源车ETF中权重达8.5%",
        confidence="高",
        risk_level="中"
    )

    # 测试钉钉（需要配置webhook）
    # dingtalk = DingTalkSender(webhook="", secret="")
    # dingtalk.send_signal(test_signal)

    print("通知模块测试完成")
