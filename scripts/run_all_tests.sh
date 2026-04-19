#!/bin/bash
# -*- coding: utf-8 -*-
"""
Jarvis PM 测试运行脚本

运行所有集成测试并生成报告
"""

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$PROJECT_ROOT/apps/api"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Jarvis PM 集成测试运行器${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查 Python 环境
echo -e "${YELLOW}[1/5] 检查 Python 环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 Python3${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ Python 版本: $PYTHON_VERSION${NC}"

# 检查 pytest
echo -e "${YELLOW}[2/5] 检查 pytest...${NC}"
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}安装 pytest...${NC}"
    pip install pytest pytest-asyncio
fi
echo -e "${GREEN}✓ pytest 已安装${NC}"

# 切换到 API 目录
cd "$API_DIR"

# 设置 Python 路径
export PYTHONPATH="$API_DIR:$PYTHONPATH"
export PYTHONIOENCODING=utf-8

echo -e "${YELLOW}[3/5] 运行单元测试...${NC}"
echo ""

# 运行模板系统测试
echo -e "${BLUE}→ 运行模板系统测试...${NC}"
python3 -m pytest tests/test_templates.py -v --tb=short 2>&1 | tee /tmp/test_templates.log
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo -e "${GREEN}✓ 模板系统测试通过${NC}"
else
    echo -e "${RED}✗ 模板系统测试失败${NC}"
fi
echo ""

# 运行集成测试
echo -e "${YELLOW}[4/5] 运行集成测试...${NC}"
echo ""

echo -e "${BLUE}→ 运行端到端集成测试...${NC}"
python3 -m pytest tests/test_integration.py -v --tb=short 2>&1 | tee /tmp/test_integration.log
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo -e "${GREEN}✓ 端到端集成测试通过${NC}"
else
    echo -e "${RED}✗ 端到端集成测试失败${NC}"
fi
echo ""

echo -e "${BLUE}→ 运行 WebSocket 集成测试...${NC}"
python3 -m pytest tests/test_websocket_integration.py -v --tb=short 2>&1 | tee /tmp/test_websocket.log
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo -e "${GREEN}✓ WebSocket 集成测试通过${NC}"
else
    echo -e "${RED}✗ WebSocket 集成测试失败${NC}"
fi
echo ""

# 生成测试报告
echo -e "${YELLOW}[5/5] 生成测试报告...${NC}"
echo ""

cat > /tmp/test_report.txt << 'EOF'
========================================
    Jarvis PM 测试报告
========================================

测试时间: $(date)
Python版本: $PYTHON_VERSION

----------------------------------------
1. 模板系统测试
   文件: tests/test_templates.py
   功能覆盖:
   - 行业检测 (医疗/金融/教育/电商)
   - 模板匹配 (病理切片借阅/医疗管理后台)
   - 合规要求检查
   - 模板应用到计划

----------------------------------------
2. 端到端集成测试
   文件: tests/test_integration.py
   功能覆盖:
   - 完整PRD工作流
   - 合规模板流程
   - 检查点交互流程
   - 组件集成 (进度+WebSocket/检查点+Strategy/模板+Planner/恢复+持久化)
   - 医疗场景测试 (切片借阅平台/管理后台)
   - 并发性能测试
   - 错误处理

----------------------------------------
3. WebSocket 集成测试
   文件: tests/test_websocket_integration.py
   功能覆盖:
   - WebSocket 连接管理
   - 进度事件流
   - Agent 状态事件
   - 检查点事件
   - 完成/错误事件
   - 并发连接测试
   - 高频更新测试

----------------------------------------
测试统计:
EOF

# 统计测试结果
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}           测试摘要${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 运行所有测试并生成摘要
python3 -m pytest tests/ -v --tb=line --co -q 2>/dev/null | grep "test session starts" -A 100 | head -20

echo ""
echo -e "${GREEN}测试运行完成!${NC}"
echo ""
echo -e "${YELLOW}详细日志:${NC}"
echo "  - 模板测试: /tmp/test_templates.log"
echo "  - 集成测试: /tmp/test_integration.log"
echo "  - WebSocket测试: /tmp/test_websocket.log"
echo "  - 测试报告: /tmp/test_report.txt"
echo ""

# 返回项目根目录
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
