#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A股涨停ETF溢价监控系统 - 启动脚本
"""

import sys
import os
import argparse
import subprocess
import atexit
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 初始化日志（必须在其他导入之前）
from config.logger import setup, LoggerSettings
from loguru import logger

def initialize_logging():
    """初始化日志系统"""
    try:
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # 从配置文件加载日志设置
        import yaml
        config_path = "config/settings.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                log_config = config.get("logging", {})
                logger_settings = LoggerSettings(
                    level=log_config.get("level", "INFO"),
                    file=log_config.get("file", "logs/monitor.log"),
                    rotation=log_config.get("rotation", "100 MB"),
                    retention=log_config.get("retention", "30 days"),
                    console_output=log_config.get("console_output", True)
                )
        else:
            logger_settings = LoggerSettings()

        # 设置日志
        manager = setup(logger_settings)

        # 注册退出时刷新日志
        def flush_logs():
            logger.remove()
            logger.info("日志已刷新并关闭")

        atexit.register(flush_logs)

        return manager
    except Exception as e:
        # 如果日志初始化失败，使用基本配置
        print(f"警告: 日志初始化失败，使用基本配置: {e}")
        basic_settings = LoggerSettings(file="logs/monitor.log")
        return setup(basic_settings)

# 初始化日志
_log_manager = initialize_logging()


def check_dependencies():
    """检查依赖是否安装"""
    # 映射：包名 -> 导入名
    required = {
        'requests': 'requests',
        'pyyaml': 'yaml',
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'beautifulsoup4': 'bs4',
        'pandas': 'pandas',
        'loguru': 'loguru'
    }
    missing = []

    for package, import_name in required.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package)

    if missing:
        print("❌ 缺少以下依赖包:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\n请运行: pip install -r requirements.txt")
        return False

    print("✓ 依赖检查通过")
    return True


def create_directories():
    """创建必要的目录"""
    dirs = ['data', 'logs', 'data/etf_holdings', 'data/signals']
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print("✓ 目录创建完成")


def build_mapping():
    """构建股票-ETF映射"""
    from backend.data.etf_holder import ETFHolderFetcher
    import yaml

    print("\n开始构建股票-ETF映射关系...")

    # 加载配置
    with open('config/stocks.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    stock_codes = [s['code'] for s in config.get('my_stocks', [])]
    etf_codes = [e['code'] for e in config.get('watch_etfs', [])]

    fetcher = ETFHolderFetcher()
    mapping = fetcher.build_stock_etf_mapping(stock_codes, etf_codes)
    fetcher.save_mapping(mapping)

    print(f"✓ 映射构建完成，覆盖 {len(mapping)} 只股票")


def run_monitor():
    """运行监控器"""
    try:
        from backend.strategy.limit_monitor import main
        main()
    except Exception as e:
        logger.exception(f"监控器运行异常: {e}")
        raise


def run_api():
    """运行API服务"""
    try:
        from backend.api.app import start_server
        start_server()
    except Exception as e:
        logger.exception(f"API服务运行异常: {e}")
        raise


def run_both():
    """同时运行监控和API"""
    import multiprocessing

    # 启动API服务
    api_process = multiprocessing.Process(target=run_api)
    api_process.start()

    print(f"\n{'='*60}")
    print("🚀 A股涨停ETF溢价监控系统")
    print(f"{'='*60}")
    print(f"\n📊 Web监控界面: http://localhost:8000/frontend/index.html")
    print(f"📖 API文档: http://localhost:8000/docs")
    print(f"\n按 Ctrl+C 停止服务\n")

    # 启动监控器
    try:
        run_monitor()
    except KeyboardInterrupt:
        logger.info("收到停止信号")
        print("\n\n正在停止服务...")
        api_process.terminate()
        api_process.join(timeout=5)
        if api_process.is_alive():
            logger.warning("API进程未能正常结束，强制终止")
            api_process.kill()
        print("服务已停止")
    except Exception as e:
        logger.exception(f"服务运行异常: {e}")
        print(f"\n错误: {e}")
        api_process.terminate()
        api_process.join(timeout=5)
        if api_process.is_alive():
            api_process.kill()
        sys.exit(1)


def run_backtest(args):
    """运行回测"""
    import yaml
    import json
    from backend.backtest import create_backtest_engine, BacktestResult

    # 加载回测配置
    config_path = "config/backtest.yaml"
    backtest_config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            backtest_config = yaml.safe_load(f)

    # CLI参数覆盖配置
    start_date = args.start_date or backtest_config.get('default_start_date', '20240101')
    end_date = args.end_date or backtest_config.get('default_end_date', '20241231')
    granularity = args.granularity or backtest_config.get('time_granularity', 'daily')
    min_weight = args.min_weight
    evaluator_type = args.evaluator_type or backtest_config.get('evaluator_type', 'default')

    print(f"\n{'='*60}")
    print("📈 ETF套利策略回测")
    print(f"{'='*60}")
    print(f"开始日期: {start_date}")
    print(f"结束日期: {end_date}")
    print(f"时间粒度: {granularity}")
    if min_weight:
        print(f"最小权重: {min_weight*100:.1f}%")
    print(f"{'='*60}\n")

    # 创建回测引擎
    engine = create_backtest_engine(
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        min_weight=min_weight,
        evaluator_type=evaluator_type,
        progress_callback=lambda p: print(f"\r进度: {p*100:.1f}%", end='', flush=True)
    )

    # 运行回测
    result = engine.run()

    # 显示结果
    print("\n\n")
    print(result.statistics.get_summary())

    # 保存结果
    output_config = backtest_config.get('output', {})
    if output_config.get('save_signals', True):
        signals_dir = output_config.get('signals_dir', 'data/historical/signals')
        os.makedirs(signals_dir, exist_ok=True)
        output_file = f"{signals_dir}/backtest_{start_date}_{end_date}_{granularity}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"\n✓ 结果已保存到: {output_file}")

        # 保存文本报告
        if 'txt' in output_config.get('formats', []):
            report_file = output_file.replace('.json', '.txt')
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(result.statistics.get_summary())
            print(f"✓ 报告已保存到: {report_file}")


def main():
    try:
        parser = argparse.ArgumentParser(description='A股涨停ETF溢价监控系统')
        subparsers = parser.add_subparsers(dest='command', help='可用命令')

        # 默认命令（向后兼容）
        parser.add_argument('command_legacy', nargs='?', default='both',
                           choices=['monitor', 'api', 'both', 'init'],
                           help='命令: monitor=只运行监控, api=只运行API, both=同时运行, init=初始化数据')

        # 回测命令
        backtest_parser = subparsers.add_parser('backtest', help='运行策略回测')
        backtest_parser.add_argument('--start-date', help='开始日期 (YYYYMMDD)')
        backtest_parser.add_argument('--end-date', help='结束日期 (YYYYMMDD)')
        backtest_parser.add_argument('--granularity', choices=['daily', '5m', '15m', '30m'],
                                    help='时间粒度')
        backtest_parser.add_argument('--min-weight', type=float, help='最小持仓权重 (0-1)')
        backtest_parser.add_argument('--evaluator-type', choices=['default', 'conservative', 'aggressive'],
                                    help='信号评估器类型')

        args = parser.parse_args()

        # 处理旧的命令格式
        if args.command is None and args.command_legacy:
            args.command = args.command_legacy

        logger.info(f"系统启动，命令: {args.command}")

        print(f"\n{'='*60}")
        print("  A股涨停ETF溢价监控系统")
        print(f"{'='*60}\n")

        # 检查依赖
        if not check_dependencies():
            logger.error("依赖检查失败，退出")
            sys.exit(1)

        # 创建目录
        create_directories()

        # 执行命令
        if args.command == 'init':
            logger.info("执行初始化命令")
            build_mapping()
            print("\n✓ 初始化完成！")
            logger.info("初始化完成")

        elif args.command == 'monitor':
            logger.info("启动监控模式")
            run_monitor()

        elif args.command == 'api':
            logger.info("启动API模式")
            run_api()

        elif args.command == 'both':
            # 检查是否有映射文件
            if not os.path.exists('data/stock_etf_mapping.json'):
                logger.info("未找到映射文件，开始初始化...")
                print("⚠️  未找到映射文件，开始初始化...")
                build_mapping()
                print()
            else:
                logger.info("找到已有映射文件")

            run_both()

        elif args.command == 'backtest':
            # 回测不需要检查映射文件
            run_backtest(args)

        logger.info("程序正常退出")

    except KeyboardInterrupt:
        logger.info("用户中断程序 (Ctrl+C)")
        print("\n程序已中断")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"程序异常退出: {e}")
        print(f"\n程序异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
