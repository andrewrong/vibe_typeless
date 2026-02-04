#!/bin/bash
# Typeless Swift 应用停止脚本

set -e

# 检查当前目录
if [ -f "stop.sh" ] && [ -f "Package.swift" ]; then
    # 已经在 TypelessApp 目录中
    :
elif [ -d "TypelessApp" ] && [ -f "TypelessApp/stop.sh" ]; then
    # 在项目根目录，进入 TypelessApp
    cd TypelessApp
else
    echo "❌ 错误：无法找到项目目录"
    echo "   请确保从以下位置之一执行此脚本："
    echo "   1. TypelessApp 目录: cd TypelessApp && ./stop.sh"
    echo "   2. 项目根目录: ./TypelessApp/stop.sh"
    exit 1
fi

echo "🛑 停止 Typeless Swift 应用..."

# 尝试从 PID 文件停止
if [ -f runtime/logs/app.pid ]; then
    PID=$(cat runtime/logs/app.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止应用 (PID: $PID)..."
        kill $PID
        sleep 1

        # 如果进程还在，强制终止
        if ps -p $PID > /dev/null 2>&1; then
            echo "强制终止..."
            kill -9 $PID
        fi

        rm runtime/logs/app.pid
        echo "✅ 应用已停止"
    else
        echo "⚠️  进程 $PID 不存在"
        rm runtime/logs/app.pid
    fi
else
    # 尝试找到并停止所有 TypelessApp 进程
    PIDS=$(pgrep -f "TypelessApp")
    if [ -n "$PIDS" ]; then
        echo "找到运行中的应用: $PIDS"
        echo $PIDS | xargs kill
        echo "✅ 应用已停止"
    else
        echo "⚠️  未找到运行中的应用"
    fi
fi

echo ""
echo "完成！"
