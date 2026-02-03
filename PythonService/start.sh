#!/bin/bash
# Typeless 快速启动脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT/PythonService"

echo "🚀 启动 Typeless 服务..."
echo ""

# 检查环境变量
if [ ! -f .env ]; then
    echo "⚠️  警告: .env 文件不存在"
    echo "   正在创建示例配置..."
    cp .env.example .env
    echo ""
    echo "📝 请编辑 .env 文件，配置你的 API 密钥:"
    echo "   - OPENAI_API_KEY 或 GEMINI_API_KEY"
    echo ""
    read -p "按 Enter 继续 (确保已配置 .env)..."
fi

# 创建日志目录
mkdir -p logs

# 启动后端
echo "📡 启动后端服务..."
uv run --prerelease=allow uvicorn src.api.server:app \
    --host 127.0.0.1 \
    --port 8000 \
    > logs/server.log 2>&1 &

BACKEND_PID=$!
echo $BACKEND_PID > logs/server.pid

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 5

# 验证后端
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ 后端服务启动成功 (PID: $BACKEND_PID)"
else
    echo "❌ 后端服务启动失败，请查看日志:"
    echo "   tail -f $PROJECT_ROOT/PythonService/logs/server.log"
    exit 1
fi

echo ""
echo "✅ 后端服务已启动！"
echo ""
echo "📍 服务地址:"
echo "   - API: http://127.0.0.1:8000"
echo "   - 文档: http://127.0.0.1:8000/docs"
echo "   - 健康检查: http://127.0.0.1:8000/health"
echo ""
echo "📋 后端日志:"
echo "   tail -f $PROJECT_ROOT/PythonService/logs/server.log"
echo ""
echo "🚀 启动 Swift 应用:"
echo "   cd $PROJECT_ROOT/../TypelessApp"
echo "   swift run TypelessApp"
echo ""
echo "🛑 停止服务:"
echo "   kill $BACKEND_PID"
echo "   或运行: ./stop.sh"
echo ""
