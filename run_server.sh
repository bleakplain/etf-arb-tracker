#!/bin/bash
# A股涨停ETF溢价监控系统 - 启动脚本

set -e

echo "=========================================="
echo "  A股涨停ETF溢价监控系统"
echo "=========================================="
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在"
    echo ""
    echo "请先创建虚拟环境:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo ""
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查Python版本
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 检查并安装依赖
echo ""
echo "检查依赖..."
missing_deps=0

python -c "import fastapi" 2>/dev/null || missing_deps=1
python -c "import uvicorn" 2>/dev/null || missing_deps=1
python -c "import requests" 2>/dev/null || missing_deps=1
python -c "import yaml" 2>/dev/null || missing_deps=1
python -c "import bs4" 2>/dev/null || missing_deps=1
python -c "import pandas" 2>/dev/null || missing_deps=1
python -c "import loguru" 2>/dev/null || missing_deps=1
python -c "import schedule" 2>/dev/null || missing_deps=1

if [ $missing_deps -eq 1 ]; then
    echo "⚠️  缺少依赖，正在安装..."
    pip install -q fastapi uvicorn requests pyyaml beautifulsoup4 pandas loguru schedule
    echo "✓ 依赖安装完成"
else
    echo "✓ 依赖检查通过"
fi

# 创建必要目录
echo ""
echo "初始化目录..."
mkdir -p data logs
echo "✓ 目录就绪"

# 检查配置文件
echo ""
echo "检查配置文件..."
if [ ! -f "config/stocks.yaml" ]; then
    echo "⚠️  自选股配置不存在"
fi

if [ ! -f "config/settings.yaml" ]; then
    echo "⚠️  系统配置不存在"
fi

echo "✓ 配置文件就绪"

# 启动服务器
echo ""
echo "=========================================="
echo "🚀 启动服务器"
echo "=========================================="
echo ""
echo "📊 Web监控界面: http://localhost:8000/"
echo "📖 API文档:     http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

# 启动Uvicorn服务器
exec python -m uvicorn backend.api.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    --reload
