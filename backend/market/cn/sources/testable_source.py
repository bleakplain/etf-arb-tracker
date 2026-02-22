"""
可测试的数据源基类

提供HTTP客户端依赖注入，便于测试
"""

import time
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from loguru import logger

from backend.market.interfaces import IHTTPClient


class TestableDataSource(ABC):
    """
    可测试的数据源基类

    通过依赖注入HTTP客户端，使数据源可以轻松mock
    """

    def __init__(self, http_client: IHTTPClient = None, request_interval: float = 5):
        """
        初始化数据源

        Args:
            http_client: HTTP客户端（None时使用真实客户端）
            request_interval: 请求间隔（秒）
        """
        self._http_client = http_client
        self._request_interval = request_interval

        if http_client is None:
            self._http_client = self._create_default_http_client()

    @abstractmethod
    def _create_default_http_client(self) -> IHTTPClient:
        """创建默认HTTP客户端"""
        pass

    def _make_request(self, url: str, headers: Dict[str, str] = None, timeout: int = 10) -> Optional[str]:
        """
        发送HTTP请求

        Args:
            url: 请求URL
            headers: 请求头
            timeout: 超时时间

        Returns:
            响应文本，失败返回None
        """
        try:
            response = self._http_client.get(url, headers=headers, timeout=timeout)

            if response.is_success:
                # 添加请求间隔，避免被限流
                if self._request_interval > 0:
                    time.sleep(self._request_interval)
                return response.text
            else:
                logger.warning(f"HTTP请求失败: status={response.status_code}, url={url}")
                return None

        except Exception as e:
            logger.error(f"HTTP请求异常: {e}, url={url}")
            return None


class RequestsHTTPClient:
    """
    基于requests的HTTP客户端实现
    """

    def __init__(self, default_headers: Dict[str, str] = None):
        """
        初始化HTTP客户端

        Args:
            default_headers: 默认请求头
        """
        import requests

        self._session = requests.Session()
        if default_headers:
            self._session.headers.update(default_headers)

    def get(self, url: str, headers: Dict[str, str] = None, timeout: int = 10):
        """发送GET请求"""
        import requests
        from backend.market.interfaces import HTTPResponse

        req_headers = {}
        if headers:
            req_headers.update(headers)

        try:
            response = self._session.get(url, headers=req_headers, timeout=timeout)
            return HTTPResponse(
                status_code=response.status_code,
                text=response.text,
                encoding=response.encoding or 'utf-8'
            )
        except requests.RequestException as e:
            logger.error(f"HTTP请求失败: {e}")
            return HTTPResponse(status_code=500, text="")


class MockHTTPClient:
    """
    Mock HTTP客户端

    用于测试，返回预设的响应
    """

    def __init__(self):
        """初始化Mock HTTP客户端"""
        from backend.market.interfaces import HTTPResponse
        self._responses: Dict[str, HTTPResponse] = {}
        self._default_response = HTTPResponse(status_code=404, text="")

    def set_response(self, url: str, response) -> None:
        """
        设置URL的响应

        Args:
            url: URL
            response: 响应对象
        """
        self._responses[url] = response

    def set_default_response(self, response) -> None:
        """
        设置默认响应

        Args:
            response: 默认响应对象
        """
        self._default_response = response

    def get(self, url: str, headers: Dict[str, str] = None, timeout: int = 10):
        """返回预设的响应"""
        return self._responses.get(url, self._default_response)

    def reset(self) -> None:
        """重置所有响应"""
        self._responses.clear()
