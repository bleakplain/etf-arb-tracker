"""
Tushare数据源 - 付费低频
用于获取财务数据、历史数据、基本面数据
"""

import pandas as pd
import time
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime

from backend.data.source_base import (
    BaseDataSource,
    SourceType,
    DataType,
    DataSourceStatus,
    SourceCapability
)
from backend.data.utils import convert_code_format, denormalize_code


class TushareDataSource(BaseDataSource):
    """
    Tushare数据源

    特点：
    - 需要token，有积分和频率限制
    - 数据质量高，经过质量控制
    - 支持财务数据、历史数据、基本面数据
    - 适合作为低频数据补充源
    """

    def __init__(self, token: str = "", priority: int = 10):
        super().__init__(
            name="tushare",
            source_type=SourceType.PAID_LOW_FREQ,
            priority=priority
        )
        self.token = token
        self._pro = None
        self._check_config()

    def _get_capability(self) -> SourceCapability:
        """定义数据源能力"""
        return SourceCapability(
            supported_types={
                DataType.STOCK_REALTIME,
                DataType.ETF_REALTIME,
                DataType.STOCK_HISTORY,
                DataType.FINANCIAL,
                DataType.INDEX,
                DataType.FUND,
            },
            realtime=True,
            historical=True,
            batch_query=True,
            max_batch_size=5000,
            requires_token=True,
            rate_limit=200
        )

    def _check_config(self) -> bool:
        """检查配置（需要token）"""
        if not self.token:
            self.metrics.status = DataSourceStatus.DISABLED
            logger.info("Tushare未配置token，已禁用")
            return False

        try:
            import tushare as ts
            ts.set_token(self.token)
            self._pro = ts.pro_api()
            logger.info("Tushare数据源初始化成功")
            return True
        except ImportError:
            logger.warning("Tushare未安装，运行: pip install tushare")
            self.metrics.status = DataSourceStatus.DISABLED
            return False
        except Exception as e:
            logger.warning(f"Tushare初始化失败: {e}")
            self.metrics.status = DataSourceStatus.DISABLED
            return False

    def fetch_stock_spot(self, stock_codes: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取A股实时行情（日线）

        注意：Tushare的实时数据实际上是每日更新的日线数据
        """
        start_time = time.time()

        if not self._pro:
            self.metrics.record_failure()
            return pd.DataFrame()

        try:
            today = datetime.now().strftime("%Y%m%d")

            if stock_codes is None:
                stock_list = self._pro.stock_basic(
                    exchange='',
                    list_status='L',
                    fields='ts_code,symbol,name'
                )
                if stock_list.empty:
                    logger.warning("Tushare获取股票列表失败")
                    self.metrics.record_failure()
                    return pd.DataFrame()

                ts_codes = stock_list['ts_code'].tolist()[:3000]
            else:
                ts_codes = [convert_code_format(c, 'tushare') for c in stock_codes]

            logger.debug(f"使用Tushare获取 {len(ts_codes)} 只股票行情...")

            # 获取每日基本行情
            df = self._pro.daily_basic(
                trade_date=today,
                ts_code=','.join(ts_codes[:2000]),
                fields='ts_code,close,turnover_rate,volume_ratio,pe,pb'
            )

            # 获取日线行情
            df_daily = self._pro.daily(
                trade_date=today,
                ts_code=','.join(ts_codes[:2000]),
                fields='ts_code,open,high,low,close,pre_close,vol,amount,pct_chg'
            )

            if df_daily.empty:
                self.metrics.record_failure()
                logger.warning("Tushare返回空数据（可能非交易时间）")
                return pd.DataFrame()

            # 合并数据
            df = pd.merge(df_daily, df, on='ts_code', how='left')

            # 转换列名
            df = df.rename(columns={
                'ts_code': 'ts_code',
                'open': '今开',
                'high': '最高',
                'low': '最低',
                'close': '最新价',
                'pre_close': '昨收',
                'vol': '成交量',
                'amount': '成交额',
                'pct_chg': '涨跌幅',
                'turnover_rate': '换手率',
                'pe': '市盈率',
                'pb': '市净率',
            })

            # 添加代码列（去掉后缀）
            df['代码'] = df['ts_code'].apply(denormalize_code)
            df['名称'] = ''

            # 调整列顺序
            df = df[['代码', 'ts_code', '名称', '最新价', '昨收', '今开', '最高', '最低',
                    '涨跌幅', '成交量', '成交额', '换手率', '市盈率', '市净率']]

            elapsed = time.time() - start_time
            self.metrics.record_success(elapsed)
            logger.info(f"Tushare成功获取 {len(df)} 只股票 (耗时: {elapsed:.2f}秒)")

            return df

        except Exception as e:
            elapsed = time.time() - start_time
            self.metrics.record_failure()
            logger.error(f"Tushare获取A股行情失败: {e}")
            return pd.DataFrame()

    def fetch_etf_spot(self, etf_codes: Optional[List[str]] = None) -> pd.DataFrame:
        """获取ETF实时行情"""
        return self.fetch_stock_spot(etf_codes)

    def fetch_by_codes(self, codes: List[str]) -> pd.DataFrame:
        """批量获取指定代码的行情"""
        return self.fetch_stock_spot(codes)

    def fetch_stock_history(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily"
    ) -> pd.DataFrame:
        """
        获取股票历史行情

        Args:
            stock_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            period: 周期 daily/weekly/monthly

        Returns:
            历史行情DataFrame
        """
        if not self._pro:
            return pd.DataFrame()

        try:
            ts_code = convert_code_format(stock_code, 'tushare')

            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")

            df = self._pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                return pd.DataFrame()

            # 转换列名
            df = df.rename(columns={
                'ts_code': '代码',
                'trade_date': '交易日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'vol': '成交量',
                'amount': '成交额',
                'pct_chg': '涨跌幅'
            })

            return df.sort_values('交易日期')

        except Exception as e:
            logger.error(f"Tushare获取历史行情失败: {e}")
            return pd.DataFrame()

    def fetch_financial(
        self,
        stock_code: str,
        report_type: str = "income"
    ) -> pd.DataFrame:
        """
        获取财务数据

        Args:
            stock_code: 股票代码
            report_type: 报表类型 income/balance/cashflow

        Returns:
            财务数据DataFrame
        """
        if not self._pro:
            return pd.DataFrame()

        try:
            ts_code = convert_code_format(stock_code, 'tushare')

            if report_type == "income":
                df = self._pro.income(ts_code=ts_code)
            elif report_type == "balance":
                df = self._pro.balances(ts_code=ts_code)
            elif report_type == "cashflow":
                df = self._pro.cashflow(ts_code=ts_code)
            else:
                return pd.DataFrame()

            return df

        except Exception as e:
            logger.error(f"Tushare获取财务数据失败: {e}")
            return pd.DataFrame()

    def fetch_stock_list(self) -> pd.DataFrame:
        """获取所有股票列表"""
        if not self._pro:
            return pd.DataFrame()

        try:
            df = self._pro.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol,name,area,industry,list_date'
            )

            # 转换列名
            df = df.rename(columns={
                'ts_code': 'TS代码',
                'symbol': '代码',
                'name': '名称',
                'area': '地区',
                'industry': '行业',
                'list_date': '上市日期'
            })

            logger.info(f"Tushare获取 {len(df)} 只股票列表")
            return df

        except Exception as e:
            logger.error(f"Tushare获取股票列表失败: {e}")
            return pd.DataFrame()


# 测试代码
if __name__ == "__main__":
    import os

    # 从环境变量获取token
    token = os.getenv("TUSHARE_TOKEN", "")

    if not token:
        print("请设置TUSHARE_TOKEN环境变量")
        exit(1)

    fetcher = TushareDataSource(token=token)

    print("=" * 60)
    print("测试Tushare数据源")
    print("=" * 60)

    # 测试获取股票列表
    print("\n=== 测试获取股票列表 ===")
    df = fetcher.fetch_stock_list()

    if not df.empty:
        print(f"成功获取 {len(df)} 只股票")
        print(df.head(10).to_string())

    # 测试获取指定股票行情
    print("\n=== 测试获取指定股票行情 ===")
    codes = ["600519.SH", "000001.SZ", "510300.SH"]
    df = fetcher.fetch_by_codes(codes)

    if not df.empty:
        print(f"成功获取 {len(df)} 只股票:")
        print(df[['代码', '最新价', '涨跌幅']].to_string())
