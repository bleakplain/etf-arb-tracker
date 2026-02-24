"""
我的股票 - 自选股管理

使用SQLite数据库存储用户自选股（我的股票）列表。
"""

import sqlite3
import threading
from typing import List, Optional, Dict, Any
from pathlib import Path
from loguru import logger
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class MyStock:
    """我的股票 - 自选股条目"""
    code: str
    name: str
    market: str
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MyStock':
        return cls(
            code=data.get('code', ''),
            name=data.get('name', ''),
            market=data.get('market', 'sh'),
            notes=data.get('notes', ''),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', '')
        )

    @classmethod
    def from_yaml_item(cls, item: Any) -> 'MyStock':
        return cls(
            code=getattr(item, 'code', ''),
            name=getattr(item, 'name', ''),
            market=getattr(item, 'market', 'sh'),
            notes=getattr(item, 'notes', ''),
            created_at='',
            updated_at=''
        )


class BaseDBRepository:
    """数据库仓储基类"""

    def __init__(self, db_path: str = "data/app.db"):
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        pass

    def close(self) -> None:
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')


class MyStockRepository(BaseDBRepository):
    """
    我的股票仓储

    管理用户自选股列表的增删改查操作。
    """

    _CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS mystock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        market TEXT NOT NULL DEFAULT 'sh',
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """

    _CREATE_INDEX_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_mystock_code ON mystock(code);",
        "CREATE INDEX IF NOT EXISTS idx_mystock_market ON mystock(market);",
    ]

    def _init_db(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(self._CREATE_TABLE_SQL)
            for index_sql in self._CREATE_INDEX_SQL:
                cursor.execute(index_sql)
            conn.commit()
            logger.debug(f"我的股票仓储初始化完成: {self._db_path}")
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库初始化失败: {e}")
            raise

    def _row_to_item(self, row: sqlite3.Row) -> MyStock:
        return MyStock(
            code=row['code'],
            name=row['name'],
            market=row['market'],
            notes=row['notes'] or '',
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def add(self, item: MyStock) -> bool:
        """添加股票"""
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            cursor.execute("""
                INSERT INTO mystock (code, name, market, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (item.code, item.name, item.market, item.notes, now, now))
            conn.commit()
            logger.info(f"添加股票: {item.code} - {item.name}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"股票已存在: {item.code}")
            return False
        except Exception as e:
            conn.rollback()
            logger.error(f"添加股票失败: {e}")
            return False

    def update(self, code: str, **kwargs) -> bool:
        """更新股票信息"""
        conn = self._get_connection()
        cursor = conn.cursor()

        valid_fields = {'name', 'market', 'notes'}
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}

        if not updates:
            return False

        updates['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [code]

        try:
            cursor.execute(
                f"UPDATE mystock SET {set_clause} WHERE code = ?;",
                values
            )
            conn.commit()
            logger.info(f"更新股票: {code}")
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"更新股票失败: {e}")
            return False

    def remove(self, code: str) -> bool:
        """删除股票"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM mystock WHERE code = ?;", (code,))
            conn.commit()
            logger.info(f"删除股票: {code}")
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"删除股票失败: {e}")
            return False

    def get(self, code: str) -> Optional[MyStock]:
        """获取单个股票"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mystock WHERE code = ?;", (code,))
        row = cursor.fetchone()
        return self._row_to_item(row) if row else None

    def get_all(self) -> List[MyStock]:
        """获取所有股票"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mystock ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    def get_by_market(self, market: str) -> List[MyStock]:
        """按市场获取股票"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM mystock WHERE market = ? ORDER BY created_at DESC;",
            (market,)
        )
        rows = cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    def clear(self) -> None:
        """清空所有股票"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM mystock;")
            conn.commit()
            logger.info("已清空所有股票")
        except Exception as e:
            conn.rollback()
            logger.error(f"清空股票失败: {e}")
            raise

    def get_count(self) -> int:
        """获取股票总数"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM mystock;")
        result = cursor.fetchone()
        return result[0] if result else 0

    def exists(self, code: str) -> bool:
        """检查股票是否存在"""
        return self.get(code) is not None

    def import_from_yaml(self, yaml_items: List[Any]) -> int:
        """从YAML配置导入股票"""
        count = 0
        for item in yaml_items:
            stock = MyStock.from_yaml_item(item)
            if not self.exists(stock.code):
                if self.add(stock):
                    count += 1
                else:
                    self.update(
                        stock.code,
                        name=stock.name,
                        market=stock.market,
                        notes=stock.notes
                    )
                    count += 1
            else:
                self.update(
                    stock.code,
                    name=stock.name,
                    market=stock.market,
                    notes=stock.notes
                )
                count += 1
        return count

    def export_to_list(self) -> List[Dict[str, Any]]:
        """导出为字典列表"""
        items = self.get_all()
        return [item.to_dict() for item in items]
