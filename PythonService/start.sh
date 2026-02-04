#!/bin/bash
# Typeless 快速启动脚本

set -e

# 检查当前目录是否正确
if [ -f "start.sh" ] && [ -f "pyproject.toml" ]; then
    # 已经在 PythonService 目录中
    PROJECT_ROOT="$(pwd)"
elif [ -d "PythonService" ] && [ -f "PythonService/start.sh" ]; then
    # 在项目根目录，进入 PythonService
    PROJECT_ROOT="$(pwd)"
    cd PythonService
else
    echo "❌ 错误：无法找到项目目录"
    echo "   请确保从以下位置之一执行此脚本："
    echo "   1. PythonService 目录: cd PythonService && ./start.sh"
    echo "   2. 项目根目录: ./PythonService/start.sh"
    exit 1
fi

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

# 创建运行时目录
mkdir -p runtime/logs runtime/models runtime/tmp

# 设置环境变量 - 模型缓存到 runtime/models
export HF_HOME="$(pwd)/runtime/models"
export HUGGINGFACE_HUB_CACHE="$(pwd)/runtime/models"
export MODEL_CACHE_DIR="$(pwd)/runtime/models"
export TMPDIR="$(pwd)/runtime/tmp"

# 启动后端
echo "📡 启动后端服务..."
echo "   模型缓存: $(pwd)/runtime/models"
echo "   日志目录: $(pwd)/runtime/logs"
echo ""

uv run --prerelease=allow uvicorn src.api.server:app \
    --host 127.0.0.1 \
    --port 28111 \
    > runtime/logs/server.log 2>&1 &

BACKEND_PID=$!
echo $BACKEND_PID > runtime/logs/server.pid

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 5

# 验证后端
if curl -s http://127.0.0.1:28111/health > /dev/null 2>&1; then
    echo "✅ 后端服务启动成功 (PID: $BACKEND_PID)"
else
    echo "❌ 后端服务启动失败，请查看日志:"
    echo "   tail -f runtime/logs/server.log"
    exit 1
fi

echo ""
echo "✅ 后端服务已启动！"
echo ""
echo "📍 服务地址:"
echo "   - API: http://127.0.0.1:28111"
echo "   - 文档: http://127.0.0.1:28111/docs"
echo "   - 健康检查: http://127.0.0.1:28111/health"
echo ""
echo "📋 后端日志:"
echo "   tail -f logs/server.log"
echo ""
echo "🚀 启动 Swift 应用:"
echo "   cd ../TypelessApp"
echo "   swift run TypelessApp"
echo ""
echo "🛑 停止服务:"
echo "   kill $BACKEND_PID"
echo "   或运行: ./stop.sh"
echo ""
