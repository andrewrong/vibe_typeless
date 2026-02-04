#!/bin/bash
# Typeless 一键启动脚本 - 同时启动后端和前端

set -e

echo "🚀 Typeless 一键启动"
echo ""

# 检查目录
if [ -d "PythonService" ] && [ -d "TypelessApp" ]; then
    # 在项目根目录
    :
else
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

# 检查后端配置
if [ ! -f "PythonService/.env" ]; then
    echo "⚠️  警告: PythonService/.env 文件不存在"
    echo "   正在创建示例配置..."
    cp PythonService/.env.example PythonService/.env
    echo ""
    echo "📝 请编辑 PythonService/.env 文件，配置你的 API 密钥:"
    echo "   - OPENAI_API_KEY 或 GEMINI_API_KEY"
    echo ""
    read -p "按 Enter 继续 (确保已配置 .env)..."
fi

echo "1️⃣ 启动后端服务..."
cd PythonService
./start.sh

# 等待后端启动
echo ""
echo "⏳ 等待后端服务就绪..."
sleep 3

# 检查后端健康
if curl -s http://127.0.0.1:28111/health > /dev/null 2>&1; then
    echo "✅ 后端服务就绪"
else
    echo "❌ 后端服务启动失败"
    exit 1
fi

echo ""
echo "2️⃣ 启动前端应用..."
cd ../TypelessApp
./start.sh

echo ""
echo "=" 60
echo "✅ Typeless 已完全启动！"
echo "=" 60
echo ""
echo "📍 服务状态:"
echo "   - 后端 API: http://127.0.0.1:28111"
echo "   - API 文档: http://127.0.0.1:28111/docs"
echo "   - Swift 应用: 运行中 (查看菜单栏图标)"
echo ""
echo "📋 查看日志:"
echo "   - 后端: tail -f PythonService/runtime/logs/server.log"
echo "   - 前端: tail -f TypelessApp/runtime/logs/app-*.log"
echo ""
echo "🛑 停止所有服务:"
echo "   ./stop-all.sh"
echo ""
echo "💡 使用提示:"
echo "   - 使用快捷键 Cmd+Shift+R 开始录音"
echo "   - 点击菜单栏图标打开预览窗口"
echo "   - 转录结果会自动注入到光标位置"
echo ""
