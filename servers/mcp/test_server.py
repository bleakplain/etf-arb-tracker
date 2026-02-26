#!/usr/bin/env python3
"""
测试脚本 - 验证ETF Arbitrage MCP服务器工具
"""

import sys
import asyncio
sys.path.insert(0, '.')

from servers.mcp.etf_arbitrage.server import mcp
from servers.mcp.etf_arbitrage.models.requests import *
from servers.mcp.etf_arbitrage.models.enums import *


async def test_tool(name: str, params_model, params_values: dict):
    """测试单个工具"""
    print(f"\n{'='*60}")
    print(f"测试工具: {name}")
    print(f"{'='*60}")

    try:
        # 创建请求参数
        params = params_model(**params_values)

        # 获取工具函数
        tool_func = None
        for tool_name, tool_info in mcp._tool_manager._tools.items():
            if tool_name == name:
                tool_func = tool_info['function']
                break

        if not tool_func:
            print(f"❌ 工具未找到: {name}")
            return False

        # 调用工具
        print(f"参数: {params_values}")
        result = await tool_func(params)

        # 显示结果（限制长度）
        if len(result) > 500:
            print(f"✅ 工具调用成功 (结果长度: {len(result)} 字符)")
            print(f"结果预览:\n{result[:500]}...")
        else:
            print(f"✅ 工具调用成功")
            print(f"结果:\n{result}")

        return True

    except Exception as e:
        print(f"❌ 工具调用失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("ETF Arbitrage MCP Server - 工具测试")
    print("="*60)

    tests = [
        # 1. 测试系统配置查询
        {
            "name": "etf_arbitrage_get_monitor_status",
            "model": dict,
            "params": {},
            "note": "获取监控状态（无需参数）"
        },

        # 2. 测试自选股列表
        {
            "name": "etf_arbitrage_list_watchlist",
            "model": ListWatchlistRequest,
            "params": {"response_format": "markdown"},
            "note": "列出当前自选股"
        },

        # 3. 测试股票-ETF映射
        {
            "name": "etf_arbitrage_get_stock_etf_mapping",
            "model": GetStockETFMappingRequest,
            "params": {"stock_code": None, "include_weights": True, "response_format": "json"},
            "note": "获取股票-ETF映射（可能为空，首次运行需初始化）"
        },
    ]

    results = []

    for test in tests:
        print(f"\n测试: {test['note']}")
        try:
            if test['model'] == dict:
                # 特殊处理（monitor_status等无参数工具）
                result = await test_tool(test['name'], test['model'], test['params'])
            else:
                result = await test_tool(test['name'], test['model'], test['params'])
            results.append((test['name'], result))
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
            results.append((test['name'], False))

    # 汇总结果
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print(f"⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
