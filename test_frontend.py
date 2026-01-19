#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
前端功能测试脚本
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    """测试API接口"""
    print("=" * 60)
    print("测试API接口")
    print("=" * 60)

    # 测试根路径
    print("\n1. 测试根路径 (GET /):")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200 and "<html" in response.text:
            print("   ✓ 前端页面加载成功")
        else:
            print(f"   ✗ 状态码: {response.status_code}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    # 测试状态API
    print("\n2. 测试状态API (GET /api/status):")
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        data = response.json()
        print(f"   ✓ 监控股票数: {data['watch_stocks_count']}")
        print(f"   ✓ 交易时间: {data['is_trading_time']}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    # 测试股票API
    print("\n3. 测试股票API (GET /api/stocks):")
    try:
        response = requests.get(f"{BASE_URL}/api/stocks")
        stocks = response.json()
        print(f"   ✓ 获取到 {len(stocks)} 只股票")
        if stocks:
            print(f"   ✓ 示例: {stocks[0]['name']} ({stocks[0]['code']}) - ¥{stocks[0]['price']:.2f}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    # 测试信号API
    print("\n4. 测试信号API (GET /api/signals):")
    try:
        response = requests.get(f"{BASE_URL}/api/signals")
        signals = response.json()
        print(f"   ✓ 获取到 {len(signals)} 条信号")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    # 测试映射API
    print("\n5. 测试映射API (GET /api/mapping):")
    try:
        response = requests.get(f"{BASE_URL}/api/mapping")
        mapping = response.json()
        print(f"   ✓ 映射关系覆盖 {len(mapping)} 只股票")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_api()
