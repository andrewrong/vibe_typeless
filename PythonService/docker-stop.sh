#!/bin/bash
# Docker 停止脚本

set -e

# 检查当前目录
if [ -f "docker-stop.sh" ] && [ -f "pyproject.toml" ]; then
    # 已经在 PythonService 目录中
    :
elif [ -d "PythonService" ] && [ -f "PythonService/docker-stop.sh" ]; then
    # 在项目根目录，进入 PythonService
    cd PythonService
else
    echo "❌ 错误：无法找到项目目录"
    echo "   请确保从以下位置之一执行此脚本："
    echo "   1. PythonService 目录: cd PythonService && ./docker-stop.sh"
    echo "   2. 项目根目录: ./PythonService/docker-stop.sh"
    exit 1
fi

echo "🛑 停止 Typeless Docker 服务..."
echo ""

# 停止服务
docker-compose down

echo ""
echo "✅ 服务已停止"
echo ""
echo "💡 提示:"
echo "   - 模型文件已保存在: ${MODEL_CACHE_PATH:-./models}"
echo "   - 完全删除数据: docker-compose down -v"
echo ""
