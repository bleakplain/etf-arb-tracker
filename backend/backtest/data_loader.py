"""
历史数据加载器 - 支持多种数据源

优先使用AKShare（免费、无限制），回退到Tushare（需要token）。
"""

import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed

from .clock import TimeGranularity


class HistoricalDataLoader:
    """
    历史数据加载器

    混合模式：AKShare优先，Tushare回退
    支持并行加载提高性能
    """

    # A股涨跌限制常量
    LIMIT_UP_MAIN_BOARD = 0.10  # 主板10%
    LIMIT_UP_STAR_BOARD = 0.20  # 科创板/创业板20%
    LIMIT_UP_ST_STOCK = 0.05    # ST股票5%

    # 最大线程数（用于并行加载）
    MAX_WORKERS = 5

    def __init__(self, cache_dir: str = "data/historical/kline"):
        """
        初始化数据加载器

        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 检查可用的数据源
        self._akshare_available = self._check_akshare()
        self._tushare_available = self._check_tushare()

        logger.info(
            f"数据源状态: AKShare={self._akshare_available}, "
            f"Tushare={self._tushare_available}"
        )

    @staticmethod
    def _get_limit_up_threshold(stock_code: str) -> float:
        """
        根据股票代码获取涨停阈值

        Args:
            stock_code: 股票代码（6位数字）

        Returns:
            涨停阈值（如0.10表示10%）
        """
        # 科创板（688xxx）
        if stock_code.startswith("688"):
            return HistoricalDataLoader.LIMIT_UP_STAR_BOARD

        # 创业板（30xxxx）
        if stock_code.startswith("300"):
            return HistoricalDataLoader.LIMIT_UP_STAR_BOARD

        # 北交所（8xxxxx, 43xxxx）
        if stock_code.startswith("8") or stock_code.startswith("43"):
            return HistoricalDataLoader.LIMIT_UP_STAR_BOARD

        # ST股票（包含ST的名称）
        # 需要配合股票名称判断，这里暂时返回主板限制
        # 在实际使用中应该从股票名称判断

        # 主板默认10%
        return HistoricalDataLoader.LIMIT_UP_MAIN_BOARD

    @staticmethod
    def _check_akshare() -> bool:
        """检查AKShare是否可用"""
        try:
            return True
        except ImportError:
            return False

    @staticmethod
    def _check_tushare() -> bool:
        """检查Tushare是否可用"""
        try:
            token = os.environ.get("TUSHARE_TOKEN")
            return bool(token)
        except ImportError:
            return False

    def load_stock_kline(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        granularity: TimeGranularity = TimeGranularity.DAILY
    ) -> Dict[datetime, Dict]:
        """
        加载股票K线数据

        Args:
            stock_code: 股票代码（6位数字）
            start_date: 开始日期 "YYYYMMDD"
            end_date: 结束日期 "YYYYMMDD"
            granularity: 时间粒度

        Returns:
            {datetime: quote_data} 字典
        """
        cache_file = self._get_cache_path(stock_code, start_date, end_date, granularity)

        # 尝试从缓存加载
        cached_data = self._load_from_cache(cache_file)
        if cached_data is not None:
            logger.debug(f"从缓存加载股票 {stock_code} 数据")
            return cached_data

        # 从数据源获取
        if self._akshare_available:
            data = self._load_stock_from_akshare(stock_code, start_date, end_date, granularity)
        elif self._tushare_available:
            data = self._load_stock_from_tushare(stock_code, start_date, end_date, granularity)
        else:
            logger.error("没有可用的数据源")
            return {}

        # 保存到缓存
        if data:
            self._save_to_cache(cache_file, data)

        return data

    def load_etf_kline(
        self,
        etf_code: str,
        start_date: str,
        end_date: str,
        granularity: TimeGranularity = TimeGranularity.DAILY
    ) -> Dict[datetime, Dict]:
        """
        加载ETF K线数据

        Args:
            etf_code: ETF代码（6位数字）
            start_date: 开始日期 "YYYYMMDD"
            end_date: 结束日期 "YYYYMMDD"
            granularity: 时间粒度

        Returns:
            {datetime: quote_data} 字典
        """
        cache_file = self._get_cache_path(etf_code, start_date, end_date, granularity, is_etf=True)

        # 尝试从缓存加载
        cached_data = self._load_from_cache(cache_file)
        if cached_data is not None:
            logger.debug(f"从缓存加载ETF {etf_code} 数据")
            return cached_data

        # 从数据源获取
        if self._akshare_available:
            data = self._load_etf_from_akshare(etf_code, start_date, end_date, granularity)
        elif self._tushare_available:
            data = self._load_etf_from_tushare(etf_code, start_date, end_date, granularity)
        else:
            logger.error("没有可用的数据源")
            return {}

        # 保存到缓存
        if data:
            self._save_to_cache(cache_file, data)

        return data

    def load_batch_kline(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        granularity: TimeGranularity = TimeGranularity.DAILY,
        is_etf: bool = False
    ) -> Dict[str, Dict[datetime, Dict]]:
        """
        批量并行加载K线数据

        Args:
            codes: 股票/ETF代码列表
            start_date: 开始日期
            end_date: 结束日期
            granularity: 时间粒度
            is_etf: 是否为ETF

        Returns:
            {code: {datetime: quote_data}} 字典
        """
        logger.info(f"开始并行加载 {len(codes)} 个标的的K线数据...")

        results = {}

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            future_to_code = {}

            for code in codes:
                if is_etf:
                    future = executor.submit(
                        self.load_etf_kline, code, start_date, end_date, granularity
                    )
                else:
                    future = executor.submit(
                        self.load_stock_kline, code, start_date, end_date, granularity
                    )
                future_to_code[future] = code

            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    data = future.result()
                    if data:
                        results[code] = data
                except Exception as e:
                    logger.error(f"加载 {code} 数据失败: {e}")

        logger.info(f"批量加载完成，成功 {len(results)}/{len(codes)}")
        return results

    def _load_stock_from_akshare(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        granularity: TimeGranularity
    ) -> Dict[datetime, Dict]:
        """使用AKShare加载股票数据"""
        try:
            import akshare as ak

            # AKShare股票代码需要加前缀
            symbol = self._format_stock_symbol(stock_code)

            # 根据粒度选择不同的API
            if granularity == TimeGranularity.DAILY:
                # 优先使用 stock_zh_a_daily API（更稳定）
                try:
                    df = ak.stock_zh_a_daily(
                        symbol=symbol,
                        start_date=start_date.replace("-", ""),  # 20240101格式
                        end_date=end_date.replace("-", ""),
                        adjust="qfq"
                    )
                    if df.empty:
                        # 如果daily API返回空，尝试hist API
                        raise ValueError("Empty data from stock_zh_a_daily")
                except Exception as e:
                    logger.debug(f"stock_zh_a_daily failed, trying stock_zh_a_hist: {e}")
                    df = ak.stock_zh_a_hist(
                        symbol=stock_code,  # hist API不需要前缀
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust=""  # 不复权，避免空数据
                    )
            else:
                # 分钟级别数据
                df = ak.stock_zh_a_hist_min_em(
                    symbol=symbol,
                    period=granularity.value,
                    adjust_date=start_date.replace("-", "")
                )

            return self._convert_df_to_dict(df, stock_code)

        except Exception as e:
            logger.warning(f"AKShare加载股票 {stock_code} 失败: {e}")
            return {}

    def _load_etf_from_akshare(
        self,
        etf_code: str,
        start_date: str,
        end_date: str,
        granularity: TimeGranularity
    ) -> Dict[datetime, Dict]:
        """使用AKShare加载ETF数据"""
        try:
            import akshare as ak

            if granularity == TimeGranularity.DAILY:
                # ETF 代码格式化（加上前缀）
                symbol = self._format_stock_symbol(etf_code)

                # 优先使用 fund_etf_hist_sina（稳定）
                try:
                    df = ak.fund_etf_hist_sina(symbol=etf_code)

                    # 如果获取了所有历史数据，需要按日期过滤
                    if not df.empty and "日期" in df.columns:
                        start_dt = datetime.strptime(start_date, "%Y%m%d")
                        end_dt = datetime.strptime(end_date, "%Y%m%d")
                        df["日期_dt"] = pd.to_datetime(df["日期"])
                        df = df[(df["日期_dt"] >= start_dt) & (df["日期_dt"] <= end_dt)]
                        df = df.drop(columns=["日期_dt"])
                except Exception as e:
                    logger.debug(f"fund_etf_hist_sina failed, trying fund_etf_hist_em: {e}")
                    df = ak.fund_etf_hist_em(
                        symbol=etf_code,
                        period="daily",
                        start_date=start_date.replace("-", ""),
                        end_date=end_date.replace("-", ""),
                        adjust="qfq"
                    )
            else:
                # ETF分钟数据
                df = ak.fund_etf_hist_min_em(
                    symbol=etf_code,
                    period=granularity.value
                )

            return self._convert_df_to_dict(df, etf_code)

        except Exception as e:
            logger.warning(f"AKShare加载ETF {etf_code} 失败: {e}")
            return {}

    def _load_stock_from_tushare(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        granularity: TimeGranularity
    ) -> Dict[datetime, Dict]:
        """使用Tushare加载股票数据"""
        try:
            import tushare as ts

            token = os.environ.get("TUSHARE_TOKEN")
            if not token:
                raise ValueError("TUSHARE_TOKEN environment variable not set")

            ts.set_token(token)
            pro = ts.pro_api()

            ts_code = self._format_tushare_code(stock_code)

            if granularity == TimeGranularity.DAILY:
                df = pro.daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                # 分钟级别需要高级接口
                logger.warning("Tushare分钟级别数据需要高级权限")
                return {}

            return self._convert_tushare_df_to_dict(df, stock_code)

        except Exception as e:
            logger.warning(f"Tushare加载股票 {stock_code} 失败: {e}")
            return {}

    def _load_etf_from_tushare(
        self,
        etf_code: str,
        start_date: str,
        end_date: str,
        granularity: TimeGranularity
    ) -> Dict[datetime, Dict]:
        """使用Tushare加载ETF数据"""
        try:
            import tushare as ts

            token = os.environ.get("TUSHARE_TOKEN")
            if not token:
                raise ValueError("TUSHARE_TOKEN environment variable not set")

            ts.set_token(token)
            pro = ts.pro_api()

            ts_code = self._format_tushare_code(etf_code)

            df = pro.fund_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            return self._convert_tushare_df_to_dict(df, etf_code)

        except Exception as e:
            logger.warning(f"Tushare加载ETF {etf_code} 失败: {e}")
            return {}

    @staticmethod
    def _format_stock_symbol(stock_code: str) -> str:
        """格式化股票代码为AKShare格式"""
        # 判断市场
        if stock_code.startswith("6"):
            return f"sh{stock_code}"
        else:
            return f"sz{stock_code}"

    @staticmethod
    def _format_tushare_code(code: str) -> str:
        """格式化代码为Tushare格式"""
        if code.startswith("6"):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"

    @staticmethod
    def _convert_df_to_dict(df, code: str) -> Dict[datetime, Dict]:
        """转换DataFrame为字典，支持多种数据格式"""
        result = {}

        if df.empty:
            return result

        # 获取该股票的涨停阈值
        limit_threshold = HistoricalDataLoader._get_limit_up_threshold(code)

        # 检测数据格式类型
        has_chinese_cols = "日期" in df.columns or "收盘" in df.columns or "涨跌幅" in df.columns

        # 对数据按日期排序
        df = df.sort_index() if hasattr(df, 'sort_index') else df

        prev_close = None  # 前一日收盘价，用于计算涨跌幅

        for _, row in df.iterrows():
            try:
                # 解析时间
                dt = HistoricalDataLoader._parse_datetime(row, df.columns)

                if dt is None:
                    continue

                # 解析价格数据
                quote_data = HistoricalDataLoader._parse_quote_data(
                    row, has_chinese_cols, prev_close
                )

                # 判断涨停（使用动态阈值）
                quote_data["is_limit_up"] = quote_data["change_pct"] >= (limit_threshold * 100)

                # 添加元数据
                quote_data["code"] = code
                quote_data["name"] = row.get("名称", row.get("name", ""))
                quote_data["timestamp"] = dt.strftime("%Y-%m-%d %H:%M:%S")

                result[dt] = quote_data
                prev_close = quote_data["price"]

            except Exception as e:
                logger.debug(f"转换行数据失败: {e}")
                continue

        return result

    @staticmethod
    def _parse_datetime(row, columns) -> Optional[datetime]:
        """解析时间字段"""
        if "日期" in columns:
            return datetime.strptime(str(row["日期"]), "%Y-%m-%d")

        if "date" in columns:
            date_val = row["date"]
            if isinstance(date_val, str):
                return datetime.strptime(date_val, "%Y-%m-%d")
            elif hasattr(date_val, "to_pydatetime"):
                return date_val.to_pydatetime()
            elif hasattr(date_val, "year"):
                return datetime.combine(date_val, datetime.min.time())
            else:
                return datetime.fromtimestamp(float(date_val))

        if "time" in columns:
            return datetime.strptime(str(row["time"]), "%Y-%m-%d %H:%M:%S")

        return None

    @staticmethod
    def _parse_quote_data(row, has_chinese_cols: bool, prev_close: Optional[float]) -> Dict:
        """解析行情数据"""
        if has_chinese_cols:
            price = float(row.get("收盘", row.get("close", 0)))
            change_pct = float(row.get("涨跌幅", row.get("change_pct", 0)))
            high = float(row.get("最高", row.get("high", 0)))
            low = float(row.get("最低", row.get("low", 0)))
            volume = float(row.get("成交量", row.get("volume", 0)))
            amount = float(row.get("成交额", row.get("amount", 0)))
        else:
            price = float(row.get("close", 0))
            high = float(row.get("high", 0))
            low = float(row.get("low", 0))
            volume = float(row.get("volume", 0))
            amount = float(row.get("amount", 0))
            change_pct = float(row.get("change_pct", 0))

            # 如果没有涨跌幅数据，自己计算
            if change_pct == 0 and prev_close is not None and prev_close > 0:
                change_pct = ((price - prev_close) / prev_close) * 100

        return {
            "price": price,
            "change_pct": change_pct,
            "high": high,
            "low": low,
            "volume": volume,
            "amount": amount
        }

    @staticmethod
    def _convert_tushare_df_to_dict(df, code: str) -> Dict[datetime, Dict]:
        """转换Tushare DataFrame为字典"""
        result = {}

        # 获取该股票的涨停阈值
        limit_threshold = HistoricalDataLoader._get_limit_up_threshold(code)

        for _, row in df.iterrows():
            try:
                dt = datetime.strptime(row["trade_date"], "%Y%m%d")

                # 判断涨停（使用动态阈值）
                change_pct = float(row.get("pct_chg", 0))
                is_limit = change_pct >= (limit_threshold * 100)

                result[dt] = {
                    "code": code,
                    "name": "",
                    "price": float(row.get("close", 0)),
                    "change_pct": change_pct,
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "volume": float(row.get("vol", 0)) * 100,  # Tushare单位是手
                    "amount": float(row.get("amount", 0)) * 1000,  # Tushare单位是千元
                    "is_limit_up": is_limit,
                    "timestamp": dt.strftime("%Y-%m-%d")
                }
            except Exception as e:
                logger.debug(f"转换Tushare行数据失败: {e}")
                continue

        return result

    def _get_cache_path(
        self,
        code: str,
        start_date: str,
        end_date: str,
        granularity: TimeGranularity,
        is_etf: bool = False
    ) -> Path:
        """获取缓存文件路径"""
        prefix = "etf" if is_etf else "stock"
        filename = f"{prefix}_{code}_{start_date}_{end_date}_{granularity.value}.json"
        return self.cache_dir / filename

    def _load_from_cache(self, cache_file: Path) -> Optional[Dict]:
        """从缓存加载数据"""
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 将字符串时间转回datetime
            result = {}
            for ts_str, quote in data.items():
                try:
                    if " " in ts_str:
                        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    else:
                        dt = datetime.strptime(ts_str, "%Y-%m-%d")
                    result[dt] = quote
                except ValueError:
                    continue

            return result
        except Exception as e:
            logger.warning(f"加载缓存失败 {cache_file}: {e}")
            return None

    def _save_to_cache(self, cache_file: Path, data: Dict) -> None:
        """保存数据到缓存"""
        try:
            # 将datetime转为字符串以便JSON序列化
            serializable_data = {
                dt.strftime("%Y-%m-%d %H:%M:%S" if dt.hour > 0 else "%Y-%m-%d"): quote
                for dt, quote in data.items()
            }

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(serializable_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.warning(f"保存缓存失败 {cache_file}: {e}")
