"""
Unit tests for Mapping Repository Interfaces

Tests the stock-ETF mapping repository implementations.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path

from backend.arbitrage.interfaces import (
    IStockETFMappingRepository,
    FileMappingRepository,
    InMemoryMappingRepository,
    IMappingRepository,
)


@pytest.mark.unit
class TestFileMappingRepository:
    """测试文件映射仓储"""

    @pytest.fixture
    def repo(self):
        # 使用临时目录作为测试目录
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test_mapping.json")
            yield FileMappingRepository(default_filepath=filepath)

    @pytest.fixture
    def sample_mapping(self):
        return {
            "600519": [
                {"etf_code": "510300", "etf_name": "沪深300ETF", "weight": 0.05},
                {"etf_code": "510500", "etf_name": "中证500ETF", "weight": 0.03},
            ],
            "000001": [
                {"etf_code": "510300", "etf_name": "沪深300ETF", "weight": 0.02}
            ]
        }

    def test_init(self):
        """测试初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test.json")
            repo = FileMappingRepository(default_filepath=filepath)
            assert repo._default_filepath == filepath
            assert repo._cached_mapping is None

    def test_load_mapping_file_not_exists(self, repo):
        """测试加载不存在的文件"""
        result = repo.load_mapping()
        assert result == {}
        assert repo._cached_mapping == {}

    def test_save_and_load_mapping(self, repo, sample_mapping):
        """测试保存和加载映射"""
        # 保存
        result = repo.save_mapping(sample_mapping)
        assert result is True
        assert repo._cached_mapping == sample_mapping

        # 加载
        loaded = repo.load_mapping()
        assert loaded == sample_mapping

    def test_save_mapping_creates_directory(self):
        """测试保存时自动创建目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 使用不存在的子目录
            subdir_path = os.path.join(temp_dir, "subdir", "test.json")
            repo = FileMappingRepository(default_filepath=subdir_path)

            sample_mapping = {"600519": [{"etf_code": "510300", "weight": 0.05}]}
            result = repo.save_mapping(sample_mapping)

            assert result is True
            assert os.path.exists(subdir_path)

            # 验证文件内容
            with open(subdir_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            assert loaded == sample_mapping

    def test_save_mapping_invalid_json(self, repo):
        """测试保存无效的映射（空字典可以保存）"""
        # 空字典应该可以保存
        result = repo.save_mapping({})
        assert result is True

    def test_load_mapping_invalid_json(self):
        """测试加载无效的JSON文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "invalid.json")
            # 创建无效的JSON文件
            with open(filepath, 'w') as f:
                f.write("{ invalid json")

            repo = FileMappingRepository(default_filepath=filepath)
            result = repo.load_mapping()
            assert result == {}

    def test_mapping_exists_true(self, repo, sample_mapping):
        """测试文件存在"""
        repo.save_mapping(sample_mapping)
        assert repo.mapping_exists() is True

    def test_mapping_exists_false(self, repo):
        """测试文件不存在"""
        assert repo.mapping_exists() is False

    def test_mapping_exists_custom_filepath(self):
        """测试使用自定义路径检查文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = FileMappingRepository(default_filepath="default.json")
            existing_file = os.path.join(temp_dir, "existing.json")
            Path(existing_file).touch()

            assert repo.mapping_exists(filepath=existing_file) is True
            assert repo.mapping_exists(filepath="nonexistent.json") is False

    def test_delete_mapping_success(self, repo, sample_mapping):
        """测试删除映射文件"""
        repo.save_mapping(sample_mapping)
        assert repo.mapping_exists() is True

        result = repo.delete_mapping()
        assert result is True
        assert repo.mapping_exists() is False
        assert repo._cached_mapping is None

    def test_delete_mapping_not_exists(self, repo):
        """测试删除不存在的文件"""
        result = repo.delete_mapping()
        assert result is False

    def test_delete_mapping_custom_filepath(self):
        """测试使用自定义路径删除"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = FileMappingRepository(default_filepath="default.json")
            existing_file = os.path.join(temp_dir, "to_delete.json")
            Path(existing_file).touch()

            result = repo.delete_mapping(filepath=existing_file)
            assert result is True
            assert not os.path.exists(existing_file)

    def test_get_etf_list_with_cache(self, repo, sample_mapping):
        """测试使用缓存获取ETF列表"""
        repo._cached_mapping = sample_mapping

        etf_list = repo.get_etf_list("600519")

        assert len(etf_list) == 2
        assert etf_list[0]["etf_code"] == "510300"
        assert etf_list[1]["etf_code"] == "510500"

    def test_get_etf_list_load_from_file(self, repo, sample_mapping):
        """测试从文件加载后获取ETF列表"""
        repo.save_mapping(sample_mapping)
        repo._cached_mapping = None  # 清除缓存

        etf_list = repo.get_etf_list("600519")

        assert len(etf_list) == 2

    def test_get_etf_list_stock_not_found(self, repo, sample_mapping):
        """测试获取不存在的股票ETF列表"""
        repo._cached_mapping = sample_mapping

        etf_list = repo.get_etf_list("999999")

        assert etf_list == []

    def test_has_stock_true(self, repo, sample_mapping):
        """测试检查存在的股票"""
        repo._cached_mapping = sample_mapping
        assert repo.has_stock("600519") is True

    def test_has_stock_false(self, repo, sample_mapping):
        """测试检查不存在的股票"""
        repo._cached_mapping = sample_mapping
        assert repo.has_stock("999999") is False

    def test_get_all_stocks(self, repo, sample_mapping):
        """测试获取所有股票代码"""
        repo._cached_mapping = sample_mapping

        stocks = repo.get_all_stocks()

        assert set(stocks) == {"600519", "000001"}

    def test_get_all_stocks_empty(self, repo):
        """测试获取所有股票代码（空映射）"""
        repo._cached_mapping = {}
        stocks = repo.get_all_stocks()
        assert stocks == []

    def test_save_mapping_updates_cache(self, repo, sample_mapping):
        """测试保存映射更新缓存"""
        assert repo._cached_mapping is None

        repo.save_mapping(sample_mapping)

        assert repo._cached_mapping == sample_mapping

    def test_load_mapping_updates_cache(self, repo, sample_mapping):
        """测试加载映射更新缓存"""
        repo.save_mapping(sample_mapping)
        repo._cached_mapping = None

        repo.load_mapping()

        assert repo._cached_mapping == sample_mapping


@pytest.mark.unit
class TestInMemoryMappingRepository:
    """测试内存映射仓储"""

    @pytest.fixture
    def repo(self):
        return InMemoryMappingRepository()

    @pytest.fixture
    def sample_mapping(self):
        return {
            "600519": [
                {"etf_code": "510300", "etf_name": "沪深300ETF", "weight": 0.05}
            ],
            "000001": [
                {"etf_code": "510500", "etf_name": "中证500ETF", "weight": 0.03}
            ]
        }

    def test_init(self, repo):
        """测试初始化"""
        assert repo._mapping == {}

    def test_load_mapping_empty(self, repo):
        """测试加载空映射"""
        result = repo.load_mapping()
        assert result == {}

    def test_load_mapping_returns_copy(self, repo, sample_mapping):
        """测试加载返回的是副本（浅拷贝）"""
        repo._mapping = sample_mapping

        result = repo.load_mapping()
        # 修改返回的字典顶层键（浅拷贝只保护这一层）
        result["999999"] = [{"etf_code": "test"}]

        # 原映射不应有新键
        assert "999999" not in repo._mapping

    def test_save_mapping(self, repo, sample_mapping):
        """测试保存映射"""
        result = repo.save_mapping(sample_mapping)
        assert result is True
        assert repo._mapping == sample_mapping

    def test_save_mapping_stores_reference(self, repo, sample_mapping):
        """测试保存后存储引用（浅拷贝）"""
        repo.save_mapping(sample_mapping)
        # InMemoryRepository使用浅拷贝，所以修改嵌套对象会影响原数据
        # 这是预期行为，用于测试
        assert repo._mapping == sample_mapping

    def test_mapping_exists_true(self, repo, sample_mapping):
        """测试映射存在"""
        repo._mapping = sample_mapping
        assert repo.mapping_exists() is True

    def test_mapping_exists_false(self, repo):
        """测试映射不存在"""
        assert repo.mapping_exists() is False

    def test_delete_mapping(self, repo, sample_mapping):
        """测试删除映射"""
        repo._mapping = sample_mapping
        assert repo.mapping_exists() is True

        result = repo.delete_mapping()
        assert result is True
        assert repo._mapping == {}

    def test_get_etf_list(self, repo, sample_mapping):
        """测试获取ETF列表"""
        repo._mapping = sample_mapping

        etf_list = repo.get_etf_list("600519")

        assert len(etf_list) == 1
        assert etf_list[0]["etf_code"] == "510300"

    def test_get_etf_list_returns_copy(self, repo, sample_mapping):
        """测试获取ETF列表返回副本（浅拷贝）"""
        repo._mapping = sample_mapping

        etf_list = repo.get_etf_list("600519")
        # 列表是浅拷贝，可以添加新元素不影响原列表
        etf_list.append({"etf_code": "test"})

        # 原映射的列表长度不应改变
        assert len(repo._mapping["600519"]) == 1

    def test_has_stock_true(self, repo, sample_mapping):
        """测试检查存在的股票"""
        repo._mapping = sample_mapping
        assert repo.has_stock("600519") is True

    def test_has_stock_false(self, repo, sample_mapping):
        """测试检查不存在的股票"""
        repo._mapping = sample_mapping
        assert repo.has_stock("999999") is False

    def test_get_all_stocks(self, repo, sample_mapping):
        """测试获取所有股票"""
        repo._mapping = sample_mapping

        stocks = repo.get_all_stocks()

        assert set(stocks) == {"600519", "000001"}

    def test_get_all_stocks_returns_list(self, repo, sample_mapping):
        """测试get_all_stocks返回列表"""
        repo._mapping = sample_mapping

        stocks = repo.get_all_stocks()

        assert isinstance(stocks, list)


@pytest.mark.unit
class TestInterfaceCompatibility:
    """测试接口兼容性"""

    def test_imapping_repository_alias(self):
        """测试IMappingRepository别名"""
        assert IMappingRepository == IStockETFMappingRepository

    def test_file_repo_implements_interface(self):
        """测试FileMappingRepository实现接口"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = FileMappingRepository(default_filepath=os.path.join(temp_dir, "test.json"))
            assert isinstance(repo, IStockETFMappingRepository)

    def test_memory_repo_implements_interface(self):
        """测试InMemoryMappingRepository实现接口"""
        repo = InMemoryMappingRepository()
        assert isinstance(repo, IStockETFMappingRepository)
