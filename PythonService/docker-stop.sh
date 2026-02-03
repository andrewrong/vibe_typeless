#!/bin/bash
# Docker 停止脚本

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

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
