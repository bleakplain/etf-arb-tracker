"""
A股持仓数据提供
"""

from typing import Optional, Dict, List
from loguru import logger
import json
from pathlib import Path


class CNHoldingProvider:
    """A股持仓数据提供器"""

    def __init__(self):
        self._source = None

    def _get_source(self):
        """获取数据源"""
        if self._source is None:
            from backend.market.cn.sources.tencent_source import TencentSource
            self._source = TencentSource()
        return self._source

    def get_etf_top_holdings(self, etf_code: str) -> Optional[Dict]:
        """获取ETF前十大持仓"""
        source = self._get_source()
        return source.get_etf_top_holdings(etf_code)

    def load_mapping(self, filepath: str) -> Optional[Dict]:
        """加载证券-ETF映射关系"""
        try:
            path = Path(filepath)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载映射文件失败: {e}")
        return None

    def save_mapping(self, mapping: Dict, filepath: str) -> None:
        """保存证券-ETF映射关系"""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
            logger.info(f"映射关系已保存到 {filepath}")
        except Exception as e:
            logger.error(f"保存映射文件失败: {e}")

    def build_stock_etf_mapping(self, stock_codes: List[str], etf_codes: List[str]) -> Dict:
        """构建证券-ETF映射关系"""
        source = self._get_source()
        return source.build_stock_etf_mapping(stock_codes, etf_codes)
