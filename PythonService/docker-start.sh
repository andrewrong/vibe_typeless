#!/bin/bash
# Docker 一键启动脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "🐳 启动 Typeless Docker 服务..."
echo ""

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi

# 检查 .env 文件
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

# 创建模型缓存目录
MODEL_CACHE_PATH="${MODEL_CACHE_PATH:-./models}"
mkdir -p "$MODEL_CACHE_PATH"
mkdir -p logs

echo "📂 模型缓存目录: $MODEL_CACHE_PATH"
echo ""

# 构建并启动服务
echo "🔨 构建 Docker 镜像..."
docker-compose build

echo ""
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
if docker-compose ps | grep -q "typeless-backend"; then
    echo "✅ Docker 服务启动成功"
    echo ""
    echo "📍 服务地址:"
    echo "   - API: http://localhost:28111"
    echo "   - 文档: http://localhost:28111/docs"
    echo "   - 健康检查: http://localhost:28111/health"
    echo ""
    echo "📋 查看日志:"
    echo "   docker-compose logs -f"
    echo ""
    echo "🛑 停止服务:"
    echo "   docker-compose down"
    echo ""
    echo "🔄 重启服务:"
    echo "   docker-compose restart"
    echo ""

    # 显示容器信息
    echo "📦 容器信息:"
    docker-compose ps
else
    echo "❌ Docker 服务启动失败"
    echo "   查看日志: docker-compose logs"
    exit 1
fi
