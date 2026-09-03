#!/bin/bash
# 项目启动脚本

echo "🚀 启动 Oncall Opinion Analyse 系统..."
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 请先安装 Python 3"
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 请先安装 Node.js"
    exit 1
fi

echo "✅ 环境检查通过"
echo ""

# 启动后端
echo "📦 启动后端服务..."
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"
echo "   后端地址: http://localhost:8000"
echo ""

# 等待后端启动
sleep 3

# 检查后端
echo "🔍 检查后端服务..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✅ 后端服务正常"
else
    echo "   ⚠️ 后端服务可能未完全启动"
fi
echo ""

# 测试 LLM
echo "🤖 测试 LLM 连接 (BUPT 网关)..."
LLM_RESULT=$(curl -s http://localhost:8000/api/llm/test-connection)
if echo "$LLM_RESULT" | grep -q '"connected"'; then
    echo "   ✅ BUPT 网关已连接 (使用默认 API Key)"
else
    echo "   ⚠️ LLM 连接状态未知"
fi
echo ""

# 启动前端
echo "🎨 启动前端服务..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..
echo "   前端 PID: $FRONTEND_PID"
echo "   前端地址: http://localhost:5173"
echo ""

echo "=========================================="
echo "🎉 系统启动完成！"
echo ""
echo "📱 访问地址:"
echo "   - 前端: http://localhost:5173"
echo "   - 后端 API: http://localhost:8000"
echo "   - API 文档: http://localhost:8000/docs"
echo ""
echo "🔑 默认配置:"
echo "   - BUPT API Key: 已预配置，可直接使用"
echo "   - 支持模型: qwen-latest, qwen-medium, deepseek-medium"
echo ""
echo "📊 数据库状态:"
echo "   - ClickHouse: 需要单独启动 (端口 9000)"
echo "   - 不启动 ClickHouse 时，数据分析功能不可用"
echo ""
echo "🛑 停止服务: kill $BACKEND_PID $FRONTEND_PID"
echo "=========================================="

# 保持脚本运行
wait
