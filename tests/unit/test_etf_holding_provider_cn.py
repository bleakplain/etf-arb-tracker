"""
单元测试 - CNETFHoldingProvider
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from backend.market.cn.etf_holding_provider import CNETFHoldingProvider


class TestCNETFHoldingProvider:
    """A股ETF持仓数据提供器测试"""

    def test_init(self):
        """测试初始化"""
        provider = CNETFHoldingProvider()
        assert provider._source is None

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_source_lazy_initialization(self, mock_tencent_class):
        """测试数据源延迟初始化"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        provider = CNETFHoldingProvider()

        # 第一次调用应该初始化
        source1 = provider._get_source()
        assert source1 == mock_source
        mock_tencent_class.assert_called_once()

        # 第二次调用应该返回缓存的实例
        source2 = provider._get_source()
        assert source2 == source1
        assert mock_tencent_class.call_count == 1

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_get_etf_top_holdings(self, mock_tencent_class):
        """测试获取ETF前十大持仓"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        expected_holdings = {
            'etf_code': '510300',
            'etf_name': '沪深300ETF',
            'top_holdings': [
                {'stock_code': '600519', 'stock_name': '贵州茅台', 'weight': 0.05}
            ],
            'total_weight': 0.85
        }
        mock_source.get_etf_top_holdings.return_value = expected_holdings

        provider = CNETFHoldingProvider()
        result = provider.get_etf_top_holdings('510300')

        assert result == expected_holdings
        mock_source.get_etf_top_holdings.assert_called_once_with('510300')

    def test_load_mapping_file_exists(self):
        """测试加载存在的映射文件"""
        import json

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_mapping = {
                '600519': [
                    {'etf_code': '510300', 'etf_name': '沪深300ETF', 'weight': 0.05}
                ]
            }
            json.dump(test_mapping, f, ensure_ascii=False)
            temp_file = f.name

        try:
            provider = CNETFHoldingProvider()
            result = provider.load_mapping(temp_file)

            assert result == test_mapping
        finally:
            os.unlink(temp_file)

    def test_load_mapping_file_not_exists(self):
        """测试加载不存在的映射文件"""
        provider = CNETFHoldingProvider()
        result = provider.load_mapping('/nonexistent/file.json')

        assert result is None

    def test_load_mapping_invalid_json(self):
        """测试加载无效的JSON文件"""
        # 创建临时文件但写入无效JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json")
            temp_file = f.name

        try:
            provider = CNETFHoldingProvider()
            result = provider.load_mapping(temp_file)

            assert result is None
        finally:
            os.unlink(temp_file)

    def test_save_mapping_success(self):
        """测试保存映射文件成功"""
        import json

        test_mapping = {
            '600519': [
                {'etf_code': '510300', 'etf_name': '沪深300ETF', 'weight': 0.05}
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, 'test_mapping.json')

            provider = CNETFHoldingProvider()
            provider.save_mapping(test_mapping, filepath)

            # 验证文件已创建且内容正确
            assert os.path.exists(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            assert saved_data == test_mapping

    def test_save_mapping_creates_directory(self):
        """测试保存映射时自动创建目录"""
        import json

        test_mapping = {
            '600519': [
                {'etf_code': '510300', 'etf_name': '沪深300ETF', 'weight': 0.05}
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # 使用不存在的子目录
            filepath = os.path.join(temp_dir, 'subdir', 'test_mapping.json')

            provider = CNETFHoldingProvider()
            provider.save_mapping(test_mapping, filepath)

            # 验证文件已创建
            assert os.path.exists(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            assert saved_data == test_mapping

    @patch('backend.market.cn.sources.tencent.TencentSource')
    def test_build_stock_etf_mapping(self, mock_tencent_class):
        """测试构建证券-ETF映射关系"""
        mock_source = Mock()
        mock_tencent_class.return_value = mock_source

        expected_mapping = {
            '600519': [
                {'etf_code': '510300', 'etf_name': '沪深300ETF', 'weight': 0.05}
            ]
        }
        mock_source.build_stock_etf_mapping.return_value = expected_mapping

        provider = CNETFHoldingProvider()
        result = provider.build_stock_etf_mapping(['600519'], ['510300'])

        assert result == expected_mapping
        mock_source.build_stock_etf_mapping.assert_called_once_with(['600519'], ['510300'])
