"""
Unit tests for API State Management

Tests the thread-safe state management for the API.
"""

import pytest
import time
import threading
from datetime import datetime

from backend.api.state import (
    MonitorState,
    APIStateManager,
    get_api_state_manager,
    reset_api_state_manager
)


@pytest.mark.unit
class TestMonitorState:
    """测试监控器状态"""

    @pytest.fixture
    def state(self):
        return MonitorState()

    def test_initial_state(self, state):
        """测试初始状态"""
        assert state.is_running is False
        assert state.start_time is None
        assert state.stop_time is None
        assert state.scan_count == 0
        assert state.uptime_seconds is None

    def test_start_monitor(self, state):
        """测试启动监控"""
        result = state.start()
        assert result is True  # 首次启动成功

        # 再次启动应该失败
        result2 = state.start()
        assert result2 is False  # 已在运行

        assert state.is_running is True
        assert state.start_time is not None

    def test_stop_monitor(self, state):
        """测试停止监控"""
        # 未启动时停止应该失败
        result = state.stop()
        assert result is False

        # 先启动
        state.start()

        # 然后停止
        result2 = state.stop()
        assert result2 is True
        assert state.is_running is False
        assert state.stop_time is not None

    def test_increment_scan_count(self, state):
        """测试增加扫描计数"""
        assert state.scan_count == 0

        count1 = state.increment_scan_count()
        assert count1 == 1
        assert state.scan_count == 1

        count2 = state.increment_scan_count()
        assert count2 == 2
        assert state.scan_count == 2

    def test_uptime_seconds(self, state):
        """测试运行时长计算"""
        # 未启动时应该返回None
        assert state.uptime_seconds is None

        # 启动后应该计算时长
        state.start()
        time.sleep(0.1)  # 等待100ms
        uptime = state.uptime_seconds
        assert uptime is not None
        assert uptime >= 0.1

    def test_get_status_info(self, state):
        """测试获取状态信息"""
        state.start()
        state.increment_scan_count()

        info = state.get_status_info()

        assert info['is_running'] is True
        assert info['scan_count'] == 1
        assert info['start_time'] is not None
        assert info['stop_time'] is None
        assert info['uptime_seconds'] is not None

    def test_stop_time_set_on_stop(self, state):
        """测试停止时间设置"""
        state.start()
        state.stop()

        assert state.stop_time is not None
        assert state.is_running is False

    def test_thread_safety(self, state):
        """测试线程安全性"""
        results = []
        errors = []

        def increment_multiple():
            try:
                for _ in range(100):
                    state.increment_scan_count()
                results.append(True)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时操作
        threads = [threading.Thread(target=increment_multiple) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0  # 没有错误
        assert len(results) == 5
        assert state.scan_count == 500  # 5个线程 × 100次

    def test_reset(self, state):
        """测试重置状态"""
        state.start()
        state.increment_scan_count()
        state.increment_scan_count()

        assert state.is_running is True
        assert state.scan_count == 2

        state.reset()

        assert state.is_running is False
        assert state.start_time is None
        assert state.stop_time is None
        assert state.scan_count == 0


@pytest.mark.unit
class TestAPIStateManager:
    """测试API状态管理器"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = get_api_state_manager()
        manager2 = get_api_state_manager()

        # 应该是同一个实例
        assert manager1 is manager2
        assert id(manager1) == id(manager2)

    def test_monitor_state_property(self):
        """测试监控器状态属性"""
        manager = get_api_state_manager()
        state = manager.monitor_state

        assert isinstance(state, MonitorState)
        assert state.is_running is False

    def test_initialized_once(self):
        """测试只初始化一次"""
        manager1 = get_api_state_manager()
        manager2 = get_api_state_manager()

        # 检查只初始化一次
        assert manager1._initialized is True
        assert manager1 is manager2


@pytest.mark.unit
class TestResetAPIStateManager:
    """测试重置API状态管理器"""

    def test_reset_clears_state(self):
        """测试重置清空状态"""
        manager = get_api_state_manager()
        state = manager.monitor_state

        # 启动监控并增加计数
        state.start()
        state.increment_scan_count()
        state.increment_scan_count()

        assert state.is_running is True
        assert state.scan_count == 2

        # 重置
        reset_api_state_manager()

        # 获取新实例应该是新的
        new_manager = get_api_state_manager()
        new_state = new_manager.monitor_state

        assert new_state.is_running is False
        assert new_state.scan_count == 0

    def test_reset_when_none(self):
        """测试重置未初始化的管理器"""
        # 先重置一次确保为None
        reset_api_state_manager()

        # 再次重置不应该出错
        reset_api_state_manager()  # 不应该抛出异常


@pytest.mark.unit
class TestMonitorStateIntegration:
    """监控器状态集成测试"""

    def test_full_lifecycle(self):
        """测试完整的生命周期"""
        state = MonitorState()

        # 初始状态
        assert state.is_running is False
        assert state.scan_count == 0

        # 启动
        assert state.start() is True
        assert state.is_running is True

        # 扫描
        state.increment_scan_count()
        assert state.scan_count == 1

        # 等待一小段时间确保uptime可以计算
        time.sleep(0.05)

        # 获取运行中的状态
        running_info = state.get_status_info()
        assert running_info['is_running'] is True
        assert running_info['uptime_seconds'] is not None
        assert running_info['uptime_seconds'] >= 0.05

        # 停止
        assert state.stop() is True
        assert state.is_running is False
        assert state.stop_time is not None

        # 获取停止后的状态
        info = state.get_status_info()
        assert info['is_running'] is False
        assert info['scan_count'] == 1
        assert info['start_time'] is not None
        assert info['stop_time'] is not None
        # 停止后uptime应该仍然是有效数值（从启动到停止的时长）
        assert info['uptime_seconds'] is not None
        assert info['uptime_seconds'] >= 0.05

    def test_concurrent_start_stop(self):
        """测试并发的启动和停止操作"""
        state = MonitorState()
        results = []

        def try_start_stop():
            for _ in range(10):
                if state.start():
                    time.sleep(0.01)
                    if state.stop():
                        results.append(True)

        threads = [threading.Thread(target=try_start_stop) for _ in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 至少有一些操作成功
        assert len(results) > 0
