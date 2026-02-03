#!/bin/bash
# Typeless 停止脚本

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT/PythonService"

echo "🛑 停止 Typeless 服务..."

# 尝试从 PID 文件停止
if [ -f logs/server.pid ]; then
    PID=$(cat logs/server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止后端服务 (PID: $PID)..."
        kill $PID
        rm logs/server.pid
        echo "✅ 后端服务已停止"
    else
        echo "⚠️  进程 $PID 不存在"
        rm logs/server.pid
    fi
else
    # 尝试找到并停止所有 uvicorn 进程
    PIDS=$(pgrep -f "uvicorn src.api.server")
    if [ -n "$PIDS" ]; then
        echo "找到运行中的后端服务: $PIDS"
        echo $PIDS | xargs kill
        echo "✅ 后端服务已停止"
    else
        echo "⚠️  未找到运行中的后端服务"
    fi
fi

echo ""
echo "完成！"
