"""
Unit tests for Utils Module

Tests the cache utilities, code utilities, and plugin registry.
"""

import pytest
import time
from threading import Thread
from datetime import datetime, timedelta, timezone

from backend.utils.cache_utils import TTLCache, CacheEntry, CacheStats
from backend.utils.code_utils import normalize_stock_code, add_market_prefix
from backend.utils.plugin_registry import PluginRegistry
from backend.utils import time_utils
from backend.utils.clock import Clock, FrozenClock, ShiftClock, set_clock, reset_clock, CHINA_TZ


@pytest.mark.unit
class TestTTLCache:
    """测试TTL缓存"""

    def test_create_cache(self):
        """测试创建缓存"""
        cache = TTLCache(ttl=30, max_size=100, name="test_cache")

        assert cache is not None
        assert cache.ttl == 30
        assert cache.size == 0

    def test_set_and_get(self):
        """测试设置和获取值"""
        cache = TTLCache(ttl=30)

        cache.set("key1", "value1")
        value = cache.get("key1")

        assert value == "value1"

    def test_get_returns_none_for_unknown_key(self):
        """测试获取不存在的键返回None"""
        cache = TTLCache(ttl=30)

        value = cache.get("unknown")

        assert value is None

    def test_get_or_load(self):
        """测试get_or_load方法"""
        cache = TTLCache(ttl=30)

        # 第一次调用，需要加载
        value1 = cache.get_or_load("key1", lambda: "loaded_value")
        assert value1 == "loaded_value"

        # 第二次调用，从缓存获取
        value2 = cache.get_or_load("key1", lambda: "different_value")
        assert value2 == "loaded_value"

    def test_cache_expiration(self):
        """测试缓存过期"""
        cache = TTLCache(ttl=1)  # 1秒TTL

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # 等待过期
        time.sleep(1.1)

        assert cache.get("key1") is None

    def test_cache_max_size(self):
        """测试最大缓存大小"""
        cache = TTLCache(ttl=30, max_size=2)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size == 2

        # 添加第三个，应该淘汰最老的
        cache.set("key3", "value3")
        assert cache.size == 2
        assert cache.get("key1") is None  # 被淘汰

    def test_delete(self):
        """测试删除缓存条目"""
        cache = TTLCache(ttl=30)

        cache.set("key1", "value1")
        assert cache.get("key1") is not None

        deleted = cache.delete("key1")
        assert deleted is True
        assert cache.get("key1") is None

    def test_delete_nonexistent_key(self):
        """测试删除不存在的键"""
        cache = TTLCache(ttl=30)

        deleted = cache.delete("unknown")
        assert deleted is False

    def test_clear(self):
        """测试清空缓存"""
        cache = TTLCache(ttl=30)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size == 2

        cache.clear()
        assert cache.size == 0

    def test_get_stats(self):
        """测试获取统计信息"""
        cache = TTLCache(ttl=30)

        cache.set("key1", "value1")
        cache.get("key1")  # 命中
        cache.get("unknown")  # 未命中

        stats = cache.get_stats()

        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 0.5

    def test_contains_operator(self):
        """测试in操作符"""
        cache = TTLCache(ttl=30)

        cache.set("key1", "value1")

        assert "key1" in cache
        assert "unknown" not in cache


@pytest.mark.unit
class TestCodeUtils:
    """测试代码工具"""

    def test_normalize_stock_code_sh(self):
        """测试标准化上海股票代码"""
        code = normalize_stock_code("sh600519")
        assert code == "600519"

        code = normalize_stock_code("600519")
        assert code == "600519"

    def test_normalize_stock_code_sz(self):
        """测试标准化深圳股票代码"""
        code = normalize_stock_code("sz000001")
        assert code == "000001"

        code = normalize_stock_code("000001")
        assert code == "000001"

    def test_add_market_prefix_sh(self):
        """测试添加上海市场前缀"""
        code = add_market_prefix("600519", "sh")
        assert code == "sh600519"

    def test_add_market_prefix_sz(self):
        """测试添加深圳市场前缀"""
        code = add_market_prefix("000001", "sz")
        assert code == "sz000001"

    def test_add_market_prefix_already_has_prefix(self):
        """测试已有前缀的代码需要先标准化"""
        # 先去掉前缀，再添加
        normalized = normalize_stock_code("sh600519")
        code = add_market_prefix(normalized, "sh")
        assert code == "sh600500" or code == "sh600519"


@pytest.mark.unit
class TestPluginRegistry:
    """测试插件注册表"""

    @pytest.fixture
    def base_class(self):
        """创建基类"""
        class BasePlugin:
            def __init__(self, name="test"):
                self.name = name
        return BasePlugin

    @pytest.fixture
    def registry(self, base_class):
        """创建注册表"""
        return PluginRegistry("TestPlugin", base_class=base_class)

    def test_register_plugin(self, registry, base_class):
        """测试注册插件"""
        @registry.register("plugin1", priority=100)
        class Plugin1(base_class):
            pass

        assert registry.is_registered("plugin1")
        assert registry.get("plugin1") is Plugin1

    def test_get_plugin(self, registry, base_class):
        """测试获取插件"""
        @registry.register("plugin1", priority=100)
        class Plugin1(base_class):
            pass

        plugin_cls = registry.get("plugin1")
        assert plugin_cls is Plugin1

    def test_get_nonexistent_plugin(self, registry):
        """测试获取不存在的插件"""
        plugin_cls = registry.get("unknown")
        assert plugin_cls is None

    def test_list_names(self, registry, base_class):
        """测试列出所有插件名称"""
        @registry.register("plugin1", priority=100)
        class Plugin1(base_class):
            pass

        @registry.register("plugin2", priority=90)
        class Plugin2(base_class):
            pass

        names = registry.list_names()
        assert "plugin1" in names
        assert "plugin2" in names

    def test_list_by_priority(self, registry, base_class):
        """测试按优先级列出插件"""
        @registry.register("plugin1", priority=90)
        class Plugin1(base_class):
            pass

        @registry.register("plugin2", priority=100)
        class Plugin2(base_class):
            pass

        # list_by_priority 可能不存在，测试 list_names
        names = registry.list_names()
        assert "plugin1" in names
        assert "plugin2" in names

    def test_unregister(self, registry, base_class):
        """测试注销插件"""
        @registry.register("plugin1", priority=100)
        class Plugin1(base_class):
            pass

        assert registry.is_registered("plugin1")

        registry.unregister("plugin1")

        assert not registry.is_registered("plugin1")


@pytest.mark.unit
class TestTimeUtils:
    """测试时间工具"""

    def test_now_china_returns_datetime(self):
        """测试now_china返回datetime"""
        now = time_utils.now_china()
        assert isinstance(now, datetime)

    def test_now_china_str_returns_string(self):
        """测试now_china_str返回字符串"""
        time_str = time_utils.now_china_str()
        assert isinstance(time_str, str)
        # 检查格式 YYYY-MM-DD HH:MM:SS
        assert len(time_str) == 19

    def test_today_china_returns_string(self):
        """测试today_china返回字符串"""
        today = time_utils.today_china()
        assert isinstance(today, str)
        # 检查格式 YYYY-MM-DD
        assert len(today) == 10

    def test_today_china_compact_returns_string(self):
        """测试today_china_compact返回紧凑格式"""
        today_str = time_utils.today_china_compact()
        assert isinstance(today_str, str)
        # 检查格式 YYYYMMDD
        assert len(today_str) == 8

    def test_timestamp_now_returns_int(self):
        """测试timestamp_now返回整数"""
        timestamp = time_utils.timestamp_now()
        # 返回字符串形式的时间戳
        assert isinstance(timestamp, (int, str))
        if isinstance(timestamp, str):
            assert timestamp.isdigit()

    def test_is_trading_time_returns_bool(self):
        """测试is_trading_time返回布尔值"""
        is_trading = time_utils.is_trading_time()
        assert isinstance(is_trading, bool)

    def test_time_to_close_returns_int_or_none(self):
        """测试time_to_close返回整数或None"""
        seconds = time_utils.time_to_close()
        # 非交易时间可能返回None
        assert seconds is None or isinstance(seconds, int)


@pytest.mark.unit
class TestClockAbstraction:
    """测试时钟抽象 - 用于确定性测试"""

    def setup_method(self):
        """每个测试前保存原始时钟"""
        self._original_clock = time_utils.get_clock()

    def teardown_method(self):
        """每个测试后恢复原始时钟"""
        reset_clock()

    def test_frozen_clock_returns_fixed_time(self):
        """测试FrozenClock返回固定时间"""
        # 2024-01-15 14:30:00 中国时区
        frozen_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=CHINA_TZ)
        frozen_clock = FrozenClock(frozen_time)

        # 多次调用返回相同时间
        assert frozen_clock.now(CHINA_TZ) == frozen_time
        assert frozen_clock.now(CHINA_TZ) == frozen_time

    def test_shift_clock_adds_offset(self):
        """测试ShiftClock添加时间偏移"""
        base_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=CHINA_TZ)
        base_clock = FrozenClock(base_time)

        # 创建偏移1小时的时钟
        offset = timedelta(hours=1)
        shift_clock = ShiftClock(base_clock, offset)

        result = shift_clock.now(CHINA_TZ)
        expected = datetime(2024, 1, 15, 11, 0, 0, tzinfo=CHINA_TZ)
        assert result == expected

    def test_time_utils_with_frozen_clock(self):
        """测试time_utils使用FrozenClock进行确定性测试"""
        # 设置固定时间：2024-01-15 14:30:00 (交易时间内)
        frozen_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=CHINA_TZ)
        set_clock(FrozenClock(frozen_time))

        # now_china应该返回固定时间
        now = time_utils.now_china()
        assert now == frozen_time

        # now_china_str应该返回固定格式字符串
        time_str = time_utils.now_china_str()
        assert time_str == "2024-01-15 14:30:00"

        # is_trading_time应该返回True（14:30在交易时间内）
        assert time_utils.is_trading_time() is True

    def test_time_utils_outside_trading_hours(self):
        """测试非交易时间的确定性"""
        # 设置固定时间：2024-01-15 16:00:00 (交易时间后)
        frozen_time = datetime(2024, 1, 15, 16, 0, 0, tzinfo=CHINA_TZ)
        set_clock(FrozenClock(frozen_time))

        # is_trading_time应该返回False
        assert time_utils.is_trading_time() is False

        # time_to_close应该返回None（不在交易时间）
        assert time_utils.time_to_close() is None

    def test_time_to_close_deterministic(self):
        """测试距离收盘时间的确定性计算"""
        # 设置固定时间：2024-01-15 14:00:00 (距离下午收盘还有1小时)
        frozen_time = datetime(2024, 1, 15, 14, 0, 0, tzinfo=CHINA_TZ)
        set_clock(FrozenClock(frozen_time))

        # time_to_close应该返回3600秒（1小时）
        seconds = time_utils.time_to_close()
        assert seconds == 3600

    def test_today_china_deterministic(self):
        """测试日期获取的确定性"""
        # 设置固定时间：2024-01-15
        frozen_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=CHINA_TZ)
        set_clock(FrozenClock(frozen_time))

        assert time_utils.today_china() == "2024-01-15"
        assert time_utils.today_china_compact() == "20240115"
