"""
数据库仓储单元测试
"""

import os
import pytest
import tempfile

from backend.signal.db_repository import DBSignalRepository
from config.mystock import MyStockRepository, MyStock
from backend.arbitrage.models import TradingSignal


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def sample_signal():
    """示例信号"""
    return TradingSignal(
        signal_id="SIG_20240101100000_0001_600519",
        timestamp="2024-01-01 10:00:00",
        stock_code="600519",
        stock_name="贵州茅台",
        stock_price=1850.0,
        limit_time="09:25:00",
        locked_amount=1234567890.0,
        change_pct=0.1001,
        etf_code="510300",
        etf_name="沪深300ETF",
        etf_weight=0.0523,
        etf_price=4.5,
        etf_premium=0.01,
        etf_amount=1000000.0,
        reason="贵州茅台 涨停 (10.01%)，在 沪深300ETF 中持仓占比 5.23% (排名第3)",
        confidence="高",
        risk_level="低",
        actual_weight=0.0523,
        weight_rank=3,
        top10_ratio=0.45
    )


class TestDBSignalRepository:
    """测试信号数据库仓储"""

    def test_init_creates_database(self, temp_db):
        """测试初始化创建数据库"""
        repo = DBSignalRepository(temp_db)
        assert os.path.exists(temp_db)

        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals';")
        result = cursor.fetchone()
        assert result is not None
        conn.close()

    def test_save_signal(self, temp_db, sample_signal):
        """测试保存单个信号"""
        repo = DBSignalRepository(temp_db)
        result = repo.save(sample_signal)

        assert result is True
        assert repo.get_count() == 1

    def test_save_duplicate_signal(self, temp_db, sample_signal):
        """测试保存重复信号"""
        repo = DBSignalRepository(temp_db)
        repo.save(sample_signal)
        result = repo.save(sample_signal)

        assert result is False
        assert repo.get_count() == 1

    def test_get_signal_by_id(self, temp_db, sample_signal):
        """测试根据ID获取信号"""
        repo = DBSignalRepository(temp_db)
        repo.save(sample_signal)

        signal = repo.get_signal(sample_signal.signal_id)
        assert signal is not None
        assert signal.signal_id == sample_signal.signal_id
        assert signal.stock_code == sample_signal.stock_code

    def test_get_all_signals(self, temp_db):
        """测试获取所有信号"""
        repo = DBSignalRepository(temp_db)

        for i in range(3):
            signal = TradingSignal(
                signal_id=f"SIG_2024010110000{i}_0001_60051{i}",
                timestamp="2024-01-01 10:00:00",
                stock_code=f"60051{i}",
                stock_name=f"股票{i}",
                stock_price=10.0,
                limit_time="",
                locked_amount=0,
                change_pct=0.1,
                etf_code="510300",
                etf_name="沪深300ETF",
                etf_weight=0.05,
                etf_price=4.5,
                etf_premium=0.01,
                etf_amount=1000000.0,
                reason=f"股票{i}涨停",
                confidence="中",
                risk_level="中",
                actual_weight=0.05,
                weight_rank=1,
                top10_ratio=0.45
            )
            repo.save(signal)

        signals = repo.get_all_signals()
        assert len(signals) == 3

    def test_clear_signals(self, temp_db, sample_signal):
        """测试清空信号"""
        repo = DBSignalRepository(temp_db)
        repo.save(sample_signal)
        assert repo.get_count() == 1

        repo.clear()
        assert repo.get_count() == 0

    def test_get_signals_by_stock(self, temp_db):
        """测试按股票代码查询"""
        repo = DBSignalRepository(temp_db)

        for i in range(3):
            signal = TradingSignal(
                signal_id=f"SIG_202401011000{i}_0001_600519",
                timestamp=f"2024-01-01 10:00:{i}",
                stock_code="600519",
                stock_name="贵州茅台",
                stock_price=1850.0,
                limit_time="",
                locked_amount=0,
                change_pct=0.1,
                etf_code="510300",
                etf_name="沪深300ETF",
                etf_weight=0.05,
                etf_price=4.5,
                etf_premium=0.01,
                etf_amount=1000000.0,
                reason="测试信号",
                confidence="中",
                risk_level="中",
                actual_weight=0.05,
                weight_rank=1,
                top10_ratio=0.45
            )
            repo.save(signal)

        other_signal = TradingSignal(
            signal_id="SIG_2024010110000_0002_000001",
            timestamp="2024-01-01 10:00:00",
            stock_code="000001",
            stock_name="平安银行",
            stock_price=10.0,
            limit_time="",
            locked_amount=0,
            change_pct=0.1,
            etf_code="510300",
            etf_name="沪深300ETF",
            etf_weight=0.05,
            etf_price=4.5,
            etf_premium=0.01,
            etf_amount=1000000.0,
            reason="测试信号",
            confidence="中",
            risk_level="中",
            actual_weight=0.05,
            weight_rank=1,
            top10_ratio=0.45
        )
        repo.save(other_signal)

        stock_signals = repo.get_signals_by_stock("600519")
        assert len(stock_signals) == 3
        assert all(s.stock_code == "600519" for s in stock_signals)

    def test_get_signal_stats(self, temp_db, sample_signal):
        """测试获取统计信息"""
        repo = DBSignalRepository(temp_db)

        stats = repo.get_signal_stats()
        assert stats['total'] == 0
        assert stats['today'] == 0

        repo.save(sample_signal)

        stats = repo.get_signal_stats()
        assert stats['total'] == 1
        assert stats['unique_stocks'] == 1
        assert stats['unique_etfs'] == 1


class TestMyStockRepository:
    """测试自选股数据库仓储"""

    def test_init_creates_database(self, temp_db):
        """测试初始化创建数据库"""
        repo = MyStockRepository(temp_db)
        assert os.path.exists(temp_db)

        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mystock';")
        result = cursor.fetchone()
        assert result is not None
        conn.close()

    def test_add_item(self, temp_db):
        """测试添加自选股"""
        repo = MyStockRepository(temp_db)
        item = MyStock(
            code="600519",
            name="贵州茅台",
            market="sh",
            notes="白酒龙头"
        )

        result = repo.add(item)
        assert result is True
        assert repo.get_count() == 1

    def test_add_duplicate_item(self, temp_db):
        """测试添加重复自选股"""
        repo = MyStockRepository(temp_db)
        item = MyStock(
            code="600519",
            name="贵州茅台",
            market="sh",
            notes="白酒龙头"
        )

        repo.add(item)
        result = repo.add(item)  # 重复添加

        assert result is False
        assert repo.get_count() == 1

    def test_get_item(self, temp_db):
        """测试获取自选股"""
        repo = MyStockRepository(temp_db)
        item = MyStock(
            code="600519",
            name="贵州茅台",
            market="sh",
            notes="白酒龙头"
        )

        repo.add(item)
        retrieved = repo.get("600519")

        assert retrieved is not None
        assert retrieved.code == "600519"
        assert retrieved.name == "贵州茅台"

    def test_update_item(self, temp_db):
        """测试更新自选股"""
        repo = MyStockRepository(temp_db)
        item = MyStock(
            code="600519",
            name="贵州茅台",
            market="sh",
            notes="白酒龙头"
        )

        repo.add(item)
        result = repo.update("600519", notes="更新后的备注")
        assert result is True

        updated = repo.get("600519")
        assert updated.notes == "更新后的备注"

    def test_remove_item(self, temp_db):
        """测试删除自选股"""
        repo = MyStockRepository(temp_db)
        item = MyStock(
            code="600519",
            name="贵州茅台",
            market="sh",
            notes="白酒龙头"
        )

        repo.add(item)
        assert repo.get_count() == 1

        result = repo.remove("600519")
        assert result is True
        assert repo.get_count() == 0

    def test_get_all(self, temp_db):
        """测试获取所有自选股"""
        repo = MyStockRepository(temp_db)

        items = [
            MyStock(code="600519", name="贵州茅台", market="sh"),
            MyStock(code="000001", name="平安银行", market="sz"),
            MyStock(code="300750", name="宁德时代", market="sz"),
        ]

        for item in items:
            repo.add(item)

        all_items = repo.get_all()
        assert len(all_items) == 3

    def test_get_by_market(self, temp_db):
        """测试按市场获取自选股"""
        repo = MyStockRepository(temp_db)

        items = [
            MyStock(code="600519", name="贵州茅台", market="sh"),
            MyStock(code="000001", name="平安银行", market="sz"),
            MyStock(code="600000", name="浦发银行", market="sh"),
        ]

        for item in items:
            repo.add(item)

        sh_items = repo.get_by_market("sh")
        sz_items = repo.get_by_market("sz")

        assert len(sh_items) == 2
        assert len(sz_items) == 1
        assert all(i.market == "sh" for i in sh_items)

    def test_exists(self, temp_db):
        """测试检查自选股是否存在"""
        repo = MyStockRepository(temp_db)
        item = MyStock(
            code="600519",
            name="贵州茅台",
            market="sh"
        )

        assert repo.exists("600519") is False

        repo.add(item)
        assert repo.exists("600519") is True

    def test_clear(self, temp_db):
        """测试清空自选股"""
        repo = MyStockRepository(temp_db)

        for i in range(5):
            item = MyStock(
                code=f"60051{i}",
                name=f"股票{i}",
                market="sh"
            )
            repo.add(item)

        assert repo.get_count() == 5

        repo.clear()
        assert repo.get_count() == 0

    def test_export_to_list(self, temp_db):
        """测试导出为列表"""
        repo = MyStockRepository(temp_db)

        items = [
            MyStock(code="600519", name="贵州茅台", market="sh", notes="白酒"),
            MyStock(code="000001", name="平安银行", market="sz", notes="银行"),
        ]

        for item in items:
            repo.add(item)

        exported = repo.export_to_list()
        assert len(exported) == 2
        assert all(isinstance(item, dict) for item in exported)
        assert exported[0]['code'] == '600519'

    def test_import_from_yaml(self, temp_db):
        """测试从YAML导入"""
        repo = MyStockRepository(temp_db)

        class YamlItem:
            def __init__(self, code, name, market="sh", notes=""):
                self.code = code
                self.name = name
                self.market = market
                self.notes = notes

        yaml_items = [
            YamlItem("600519", "贵州茅台", "sh", "白酒龙头"),
            YamlItem("000001", "平安银行", "sz", "银行龙头"),
        ]

        count = repo.import_from_yaml(yaml_items)
        assert count == 2
        assert repo.get_count() == 2
        assert repo.exists("600519")
