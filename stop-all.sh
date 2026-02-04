#!/bin/bash
# Typeless 一键停止脚本 - 停止后端和前端

set -e

echo "🛑 停止 Typeless 服务"
echo ""

# 检查目录
if [ -d "PythonService" ] && [ -d "TypelessApp" ]; then
    # 在项目根目录
    :
else
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

echo "1️⃣ 停止前端应用..."
cd TypelessApp
./stop.sh

echo ""
echo "2️⃣ 停止后端服务..."
cd ../PythonService
./stop.sh

echo ""
echo "✅ 所有服务已停止"
echo ""
echo "🔄 重新启动:"
echo "   ./start-all.sh"
echo ""
