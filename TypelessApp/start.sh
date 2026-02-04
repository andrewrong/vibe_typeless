#!/bin/bash
# Typeless Swift 应用启动脚本

set -e

# 检查当前目录
if [ -f "start.sh" ] && [ -f "Package.swift" ]; then
    # 已经在 TypelessApp 目录中
    :
elif [ -d "TypelessApp" ] && [ -f "TypelessApp/start.sh" ]; then
    # 在项目根目录，进入 TypelessApp
    cd TypelessApp
else
    echo "❌ 错误：无法找到项目目录"
    echo "   请确保从以下位置之一执行此脚本："
    echo "   1. TypelessApp 目录: cd TypelessApp && ./start.sh"
    echo "   2. 项目根目录: ./TypelessApp/start.sh"
    exit 1
fi

echo "🚀 启动 Typeless Swift 应用..."
echo ""

# 创建运行时目录
mkdir -p runtime/logs runtime/tmp

# 设置日志文件路径
LOG_FILE="$(pwd)/runtime/logs/app-$(date +%Y%m%d-%H%M%S).log"
PID_FILE="$(pwd)/runtime/logs/app.pid"

echo "📝 日志文件: $LOG_FILE"
echo ""

# 启动 Swift 应用，重定向输出到日志文件
swift run TypelessApp > "$LOG_FILE" 2>&1 &
APP_PID=$!

# 保存 PID
echo $APP_PID > "$PID_FILE"

echo "✅ Swift 应用已启动 (PID: $APP_PID)"
echo ""
echo "📋 查看日志:"
echo "   tail -f $LOG_FILE"
echo ""
echo "🛑 停止应用:"
echo "   kill $APP_PID"
echo "   或运行: ./stop.sh"
echo ""

# 等待几秒检查应用是否成功启动
sleep 2

if ps -p $APP_PID > /dev/null 2>&1; then
    echo "✅ 应用运行中"
    echo ""
    echo "💡 提示:"
    echo "   - 应用应该在菜单栏显示图标"
    echo "   - 使用快捷键开始录音（默认 Cmd+Shift+R）"
    echo "   - 查看日志了解详细运行情况"
else
    echo "⚠️  应用可能已退出，请查看日志:"
    echo "   cat $LOG_FILE"
fi
