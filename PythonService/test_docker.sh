#!/bin/bash
# Docker 部署验证脚本

echo "🧪 验证 Docker 部署..."
echo ""

# 检查 Docker 是否运行
echo "1️⃣ 检查 Docker 环境..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi
echo "✅ Docker 运行中"

# 检查 docker-compose
echo ""
echo "2️⃣ 检查 docker-compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose 未安装"
    exit 1
fi
echo "✅ docker-compose 已安装"

# 检查配置文件
echo ""
echo "3️⃣ 检查配置文件..."
missing_files=()

if [ ! -f Dockerfile ]; then
    missing_files+=("Dockerfile")
fi

if [ ! -f docker-compose.yml ]; then
    missing_files+=("docker-compose.yml")
fi

if [ ! -f .env ]; then
    missing_files+=(".env")
fi

if [ ${#missing_files[@]} -gt 0 ]; then
    echo "⚠️  缺少文件: ${missing_files[*]}"
    echo "   请确保所有必需文件存在"
    exit 1
fi
echo "✅ 配置文件完整"

# 验证 .env 配置
echo ""
echo "4️⃣ 检查环境变量配置..."
source .env 2>/dev/null || true

if [ -z "$AI_PROVIDER" ] && [ -z "$OPENAI_API_KEY" ] && [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  未检测到 AI API 密钥配置"
    echo "   请在 .env 文件中配置以下之一:"
    echo "   - OPENAI_API_KEY"
    echo "   - GEMINI_API_KEY"
    echo "   - OLLAMA_BASE_URL"
else
    echo "✅ AI Provider 已配置"
fi

# 检查模型缓存目录
echo ""
echo "5️⃣ 检查模型缓存目录..."
MODEL_CACHE="${MODEL_CACHE_PATH:-./models}"
if [ ! -d "$MODEL_CACHE" ]; then
    echo "📁 创建模型缓存目录: $MODEL_CACHE"
    mkdir -p "$MODEL_CACHE"
else
    echo "✅ 模型缓存目录存在: $MODEL_CACHE"
fi

# 检查 Docker 镜像
echo ""
echo "6️⃣ 检查 Docker 镜像..."
if docker images | grep -q "pythonservice"; then
    echo "✅ Docker 镜像已存在"
else
    echo "⏳ Docker 镜像不存在，首次启动需要构建..."
fi

# 检查端口占用
echo ""
echo "7️⃣ 检查端口占用..."
if lsof -i :28111 > /dev/null 2>&1; then
    if docker ps | grep -q "typeless-backend"; then
        echo "⚠️  端口 8000 已被 Docker 容器使用"
    else
        echo "⚠️  端口 8000 被其他进程占用"
        echo "   占用进程:"
        lsof -i :28111 | tail -n +2
    fi
else
    echo "✅ 端口 8000 可用"
fi

# 验证 docker-compose 配置
echo ""
echo "8️⃣ 验证 docker-compose 配置..."
if docker-compose config > /dev/null 2>&1; then
    echo "✅ docker-compose 配置有效"
else
    echo "❌ docker-compose 配置无效"
    docker-compose config
    exit 1
fi

echo ""
echo "=" 60
echo "✅ Docker 部署验证完成！"
echo ""
echo "📍 下一步:"
echo "   构建并启动服务:"
echo "     ./docker-start.sh"
echo ""
echo "   或手动构建:"
echo "     docker-compose build"
echo "     docker-compose up -d"
echo ""
