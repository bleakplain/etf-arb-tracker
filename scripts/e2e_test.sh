#!/bin/bash
# 端到端测试快速验证脚本
# 用于在正式测试前快速验证核心功能

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=================================="
echo "端到端测试快速验证"
echo "=================================="
echo ""

# 1. 单元测试（快速验证）
echo "[1/5] 运行单元测试..."
python3 -m pytest tests/unit/ -v --tb=short -q 2>&1 | tail -5
echo "✅ 单元测试完成"
echo ""

# 2. 模块导入测试
echo "[2/5] 验证模块导入..."
python3 -c "
from backend.api.app import app
from backend.api.dependencies import register_strategies
from backend.arbitrage.strategy_registry import event_detector_registry, fund_selector_registry

# 注册策略
register_strategies()

# 验证核心策略已注册
assert 'limit_up_cn' in event_detector_registry.list_names()
assert 'highest_weight' in fund_selector_registry.list_names()
print('✅ 模块导入验证通过')
"
echo ""

# 3. API健康检查测试
echo "[3/5] 测试API健康检查..."
python3 -c "
from fastapi.testclient import TestClient
from backend.api.app import app

client = TestClient(app)
response = client.get('/api/health')
assert response.status_code == 200
assert response.json()['status'] == 'healthy'
print('✅ API健康检查通过')
"
echo ""

# 4. 配置验证测试
echo "[4/5] 验证系统配置..."
python3 -c "
import yaml
with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

# 验证关键配置存在
assert 'strategy' in config
assert 'min_weight' in config['strategy']
assert 'trading_hours' in config
print('✅ 配置验证通过')
"
echo ""

# 5. 数据库连接测试
echo "[5/5] 测试数据库连接..."
python3 -c "
import sqlite3
import os

db_path = 'data/app.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
    tables = cursor.fetchall()
    conn.close()
    print(f'✅ 数据库连接正常，包含 {len(tables)} 个表')
else:
    print('ℹ️  数据库文件不存在（首次运行正常）')
"
echo ""

echo "=================================="
echo "端到端快速验证完成 ✅"
echo "=================================="
echo ""
echo "运行完整测试套件:"
echo "  python3 -m pytest tests/unit/     # 单元测试 (~25秒)"
echo "  python3 -m pytest tests/integration/  # 集成测试 (~20分钟)"
echo ""
