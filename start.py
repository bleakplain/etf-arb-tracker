#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A股涨停ETF溢价监控系统 - 启动脚本
"""

import sys
import os
import argparse
import subprocess

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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
    from backend.strategy.limit_monitor import main
    main()


def run_api():
    """运行API服务"""
    from backend.api.app import start_server
    start_server()


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
        print("\n\n正在停止服务...")
        api_process.terminate()
        api_process.join()
        print("服务已停止")


def main():
    parser = argparse.ArgumentParser(description='A股涨停ETF溢价监控系统')
    parser.add_argument('command', nargs='?', default='both',
                       choices=['monitor', 'api', 'both', 'init'],
                       help='命令: monitor=只运行监控, api=只运行API, both=同时运行, init=初始化数据')

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("  A股涨停ETF溢价监控系统")
    print(f"{'='*60}\n")

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 创建目录
    create_directories()

    # 执行命令
    if args.command == 'init':
        build_mapping()
        print("\n✓ 初始化完成！")

    elif args.command == 'monitor':
        run_monitor()

    elif args.command == 'api':
        run_api()

    elif args.command == 'both':
        # 检查是否有映射文件
        if not os.path.exists('data/stock_etf_mapping.json'):
            print("⚠️  未找到映射文件，开始初始化...")
            build_mapping()
            print()

        run_both()


if __name__ == "__main__":
    main()
