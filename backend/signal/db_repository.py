"""
信号数据库仓储 - DBSignalRepository

使用SQLite数据库存储交易信号，提供高效的查询和更新功能。
"""

import sqlite3
import threading
from typing import List, Optional, Dict
from pathlib import Path
from loguru import logger


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


class DBSignalRepository(BaseDBRepository):
    """
    信号数据库仓储

    使用SQLite数据库存储交易信号，提供高效的查询和更新功能。
    """

    _CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS signals (
        signal_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        stock_code TEXT NOT NULL,
        stock_name TEXT NOT NULL,
        stock_price REAL,
        limit_time TEXT,
        locked_amount REAL DEFAULT 0,
        change_pct REAL,
        etf_code TEXT NOT NULL,
        etf_name TEXT NOT NULL,
        etf_weight REAL,
        etf_price REAL DEFAULT 0,
        etf_premium REAL DEFAULT 0,
        etf_amount REAL DEFAULT 0,
        reason TEXT,
        confidence TEXT DEFAULT '',
        risk_level TEXT DEFAULT '',
        actual_weight REAL,
        weight_rank INTEGER,
        top10_ratio REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """

    _CREATE_INDEXES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_signals_stock_code ON signals(stock_code);",
        "CREATE INDEX IF NOT EXISTS idx_signals_etf_code ON signals(etf_code);",
        "CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals(created_at);",
    ]

    def _init_db(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(self._CREATE_TABLE_SQL)
            for index_sql in self._CREATE_INDEXES_SQL:
                cursor.execute(index_sql)
            conn.commit()
            logger.debug(f"信号仓储初始化完成: {self._db_path}")
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库初始化失败: {e}")
            raise

    def _row_to_signal(self, row: sqlite3.Row):
        from backend.arbitrage.models import TradingSignal
        return TradingSignal(
            signal_id=row['signal_id'],
            timestamp=row['timestamp'],
            stock_code=row['stock_code'],
            stock_name=row['stock_name'],
            stock_price=row['stock_price'],
            limit_time=row['limit_time'],
            locked_amount=row['locked_amount'],
            change_pct=row['change_pct'],
            etf_code=row['etf_code'],
            etf_name=row['etf_name'],
            etf_weight=row['etf_weight'],
            etf_price=row['etf_price'],
            etf_premium=row['etf_premium'],
            etf_amount=row['etf_amount'],
            reason=row['reason'],
            confidence=row['confidence'],
            risk_level=row['risk_level'],
            actual_weight=row['actual_weight'],
            weight_rank=row['weight_rank'],
            top10_ratio=row['top10_ratio']
        )

    def save(self, signal) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO signals (
                    signal_id, timestamp, stock_code, stock_name, stock_price, limit_time,
                    locked_amount, change_pct, etf_code, etf_name, etf_weight, etf_price,
                    etf_premium, etf_amount, reason, confidence, risk_level, actual_weight,
                    weight_rank, top10_ratio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                signal.signal_id, signal.timestamp, signal.stock_code,
                signal.stock_name, signal.stock_price, signal.limit_time,
                signal.locked_amount, signal.change_pct, signal.etf_code,
                signal.etf_name, signal.etf_weight, signal.etf_price,
                signal.etf_premium, signal.etf_amount, signal.reason,
                signal.confidence, signal.risk_level, signal.actual_weight,
                signal.weight_rank, signal.top10_ratio
            ))
            conn.commit()
            logger.debug(f"保存信号: {signal.stock_name} -> {signal.etf_name}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"信号已存在: {signal.signal_id}")
            return False
        except Exception as e:
            conn.rollback()
            logger.error(f"保存信号失败: {e}")
            return False

    def save_all(self, signals) -> None:
        if not signals:
            return

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            for signal in signals:
                cursor.execute("""
                    INSERT INTO signals (
                        signal_id, timestamp, stock_code, stock_name, stock_price, limit_time,
                        locked_amount, change_pct, etf_code, etf_name, etf_weight, etf_price,
                        etf_premium, etf_amount, reason, confidence, risk_level, actual_weight,
                        weight_rank, top10_ratio
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    signal.signal_id, signal.timestamp, signal.stock_code,
                    signal.stock_name, signal.stock_price, signal.limit_time,
                    signal.locked_amount, signal.change_pct, signal.etf_code,
                    signal.etf_name, signal.etf_weight, signal.etf_price,
                    signal.etf_premium, signal.etf_amount, signal.reason,
                    signal.confidence, signal.risk_level, signal.actual_weight,
                    signal.weight_rank, signal.top10_ratio
                ))
            conn.commit()
            logger.info(f"批量保存 {len(signals)} 个信号")
        except Exception as e:
            conn.rollback()
            logger.error(f"批量保存信号失败: {e}")
            raise

    def get_all_signals(self) -> List:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals ORDER BY timestamp DESC;")
        rows = cursor.fetchall()
        return [self._row_to_signal(row) for row in rows]

    def get_today_signals(self) -> List:
        from backend.utils.time_utils import today_china
        today = today_china()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM signals WHERE timestamp LIKE ? ORDER BY timestamp DESC;",
            (f"{today}%",)
        )
        rows = cursor.fetchall()
        return [self._row_to_signal(row) for row in rows]

    def get_recent_signals(self, limit: int = 20) -> List:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?;",
            (limit,)
        )
        rows = cursor.fetchall()
        return [self._row_to_signal(row) for row in rows]

    def clear(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM signals;")
            conn.commit()
            logger.info("已清空所有信号")
        except Exception as e:
            conn.rollback()
            logger.error(f"清空信号失败: {e}")
            raise

    def get_count(self) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM signals;")
        result = cursor.fetchone()
        return result[0] if result else 0

    def get_signal(self, signal_id: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signals WHERE signal_id = ?;", (signal_id,))
        row = cursor.fetchone()
        return self._row_to_signal(row) if row else None

    def _get_signals_by_field(self, field_name: str, value: str, limit: int = None) -> List:
        """按字段查询信号的通用方法"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if limit:
            cursor.execute(
                f"SELECT * FROM signals WHERE {field_name} = ? ORDER BY timestamp DESC LIMIT ?;",
                (value, limit)
            )
        else:
            cursor.execute(
                f"SELECT * FROM signals WHERE {field_name} = ? ORDER BY timestamp DESC;",
                (value,)
            )
        return [self._row_to_signal(row) for row in cursor.fetchall()]

    def get_signals_by_stock(self, stock_code: str, limit: int = None) -> List:
        return self._get_signals_by_field('stock_code', stock_code, limit)

    def get_signals_by_etf(self, etf_code: str, limit: int = None) -> List:
        return self._get_signals_by_field('etf_code', etf_code, limit)

    def get_signals_by_date_range(self, start_date: str, end_date: str) -> List:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM signals WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp DESC;",
            (f"{start_date} 00:00:00", f"{end_date} 23:59:59")
        )
        rows = cursor.fetchall()
        return [self._row_to_signal(row) for row in rows]

    def get_signal_stats(self) -> Dict[str, int]:
        conn = self._get_connection()
        cursor = conn.cursor()

        stats = {}
        cursor.execute("SELECT COUNT(*) FROM signals;")
        stats['total'] = cursor.fetchone()[0]

        from backend.utils.time_utils import today_china
        today = today_china()
        cursor.execute("SELECT COUNT(*) FROM signals WHERE timestamp LIKE ?;", (f"{today}%",))
        stats['today'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT stock_code) FROM signals;")
        stats['unique_stocks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT etf_code) FROM signals;")
        stats['unique_etfs'] = cursor.fetchone()[0]

        return stats
