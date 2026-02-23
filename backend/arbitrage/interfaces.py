"""
Arbitrage module interfaces

Defines the core interfaces for the arbitrage module.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pathlib import Path


class IStockETFMappingRepository(ABC):
    """
    股票-ETF映射仓储接口

    用于抽象映射数据的存储、加载和查询操作
    提供默认实现以减少子类重复代码
    """

    # =========================================================================
    # 持久化操作（子类必须实现）
    # =========================================================================

    @abstractmethod
    def _get_mapping(self) -> Dict[str, List[Dict]]:
        """
        获取当前映射数据（子类实现）

        Returns:
            股票代码到ETF列表的映射字典
        """
        pass

    @abstractmethod
    def load_mapping(self, filepath: str = None) -> Dict[str, List[Dict]]:
        """
        加载股票-ETF映射关系

        Args:
            filepath: 映射文件路径，None表示使用默认路径

        Returns:
            股票代码到ETF列表的映射字典
        """
        pass

    @abstractmethod
    def save_mapping(self, mapping: Dict[str, List[Dict]], filepath: str = None) -> bool:
        """
        保存股票-ETF映射关系

        Args:
            mapping: 股票代码到ETF列表的映射字典
            filepath: 映射文件路径，None表示使用默认路径

        Returns:
            是否保存成功
        """
        pass

    @abstractmethod
    def mapping_exists(self, filepath: str = None) -> bool:
        """
        检查映射文件是否存在

        Args:
            filepath: 映射文件路径，None表示使用默认路径

        Returns:
            文件是否存在
        """
        pass

    @abstractmethod
    def delete_mapping(self, filepath: str = None) -> bool:
        """
        删除映射文件

        Args:
            filepath: 映射文件路径，None表示使用默认路径

        Returns:
            是否删除成功
        """
        pass

    # =========================================================================
    # 查询操作（默认实现，子类可覆盖）
    # =========================================================================

    def get_etf_list(self, stock_code: str) -> List[Dict]:
        """
        获取包含指定股票的ETF列表

        Args:
            stock_code: 股票代码（6位数字）

        Returns:
            ETF列表，每个ETF包含code、name、weight等字段
            如果股票不存在于映射中，返回空列表
        """
        mapping = self._get_mapping()
        return mapping.get(stock_code, []).copy()

    def has_stock(self, stock_code: str) -> bool:
        """
        检查映射中是否包含指定股票

        Args:
            stock_code: 股票代码（6位数字）

        Returns:
            是否包含该股票的映射
        """
        return stock_code in self._get_mapping()

    def get_all_stocks(self) -> List[str]:
        """
        获取所有已映射的股票代码列表

        Returns:
            股票代码列表
        """
        return list(self._get_mapping().keys())


# 向后兼容的别名
IMappingRepository = IStockETFMappingRepository


class FileMappingRepository(IStockETFMappingRepository):
    """
    基于文件的映射仓储实现

    使用JSON文件存储映射关系
    """

    def __init__(self, default_filepath: str = "data/stock_etf_mapping.json"):
        """
        初始化文件映射仓储

        Args:
            default_filepath: 默认映射文件路径
        """
        self._default_filepath = default_filepath
        self._cached_mapping: Optional[Dict[str, List[Dict]]] = None

    # =========================================================================
    # 实现抽象方法
    # =========================================================================

    def _get_mapping(self) -> Dict[str, List[Dict]]:
        """获取当前映射（从缓存或加载）"""
        return self._cached_mapping or self.load_mapping()

    def load_mapping(self, filepath: str = None) -> Dict[str, List[Dict]]:
        """从文件加载映射关系"""
        import json
        from loguru import logger

        target_path = filepath or self._default_filepath

        try:
            path = Path(target_path)
            if not path.exists():
                logger.debug(f"映射文件不存在: {target_path}")
                self._cached_mapping = {}
                return {}

            with open(path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)

            self._cached_mapping = mapping
            logger.info(f"从 {target_path} 加载了 {len(mapping)} 个股票的映射")
            return mapping

        except Exception as e:
            logger.warning(f"加载映射文件失败 ({target_path}): {e}")
            self._cached_mapping = {}
            return {}

    def save_mapping(self, mapping: Dict[str, List[Dict]], filepath: str = None) -> bool:
        """保存映射关系到文件"""
        import json
        from loguru import logger

        target_path = filepath or self._default_filepath

        try:
            path = Path(target_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)

            self._cached_mapping = mapping
            logger.info(f"映射关系已保存到 {target_path}")
            return True

        except Exception as e:
            logger.error(f"保存映射文件失败 ({target_path}): {e}")
            return False

    def mapping_exists(self, filepath: str = None) -> bool:
        """检查映射文件是否存在"""
        target_path = filepath or self._default_filepath
        return Path(target_path).exists()

    def delete_mapping(self, filepath: str = None) -> bool:
        """删除映射文件"""
        from loguru import logger

        target_path = filepath or self._default_filepath

        try:
            path = Path(target_path)
            if path.exists():
                path.unlink()
                self._cached_mapping = None
                logger.info(f"已删除映射文件: {target_path}")
                return True
            return False

        except Exception as e:
            logger.warning(f"删除映射文件失败 ({target_path}): {e}")
            return False


class InMemoryMappingRepository(IStockETFMappingRepository):
    """
    内存映射仓储实现

    仅用于测试，不进行持久化
    """

    def __init__(self):
        """初始化内存映射仓储"""
        self._mapping: Dict[str, List[Dict]] = {}

    # =========================================================================
    # 实现抽象方法
    # =========================================================================

    def _get_mapping(self) -> Dict[str, List[Dict]]:
        """获取当前映射"""
        return self._mapping

    def load_mapping(self, filepath: str = None) -> Dict[str, List[Dict]]:
        """从内存加载映射关系"""
        return self._mapping.copy()

    def save_mapping(self, mapping: Dict[str, List[Dict]], filepath: str = None) -> bool:
        """保存映射关系到内存"""
        self._mapping = mapping.copy()
        return True

    def mapping_exists(self, filepath: str = None) -> bool:
        """检查映射是否存在"""
        return len(self._mapping) > 0

    def delete_mapping(self, filepath: str = None) -> bool:
        """清除内存中的映射"""
        self._mapping.clear()
        return True
