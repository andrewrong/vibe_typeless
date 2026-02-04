#!/bin/bash
# 性能对比测试脚本 - 本地 vs Docker

echo "🧪 Typeless 性能对比测试"
echo ""

# 检查测试文件
if [ ! -f "test_audio.wav" ]; then
    echo "❌ 测试文件不存在: test_audio.wav"
    echo "   请确保测试音频文件在当前目录"
    exit 1
fi

echo "📊 测试音频: test_audio.wav"
echo ""

# 获取音频时长
DURATION=$(ffprobe -i test_audio.wav 2>&1 | grep Duration | awk '{print $2}' | cut -d'.' -f1)
echo "   音频时长: ${DURATION} 秒"
echo ""

# 测试函数
test_transcription() {
    local url=$1
    local mode=$2

    echo "▶️  测试 $mode..."
    echo "   URL: $url"

    START_TIME=$(date +%s.%N)

    RESULT=$(curl -s -X POST \
        -H "Content-Type: application/octet-stream" \
        --data-binary @test_audio.wav \
        "$url/api/asr/transcribe")

    END_TIME=$(date +%s.%N)

    # 计算耗时（秒）
    ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)

    echo "   耗时: ${ELAPSED} 秒"

    # 提取转录文本
    if echo "$RESULT" | grep -q "transcript"; then
        TRANSCRIPT=$(echo "$RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('transcript', 'N/A'))" 2>/dev/null)
        echo "   转录: '${TRANSCRIPT:0:50}...'"
    else
        echo "   ❌ 转录失败"
        echo "   响应: $RESULT"
    fi

    echo ""
}

echo "=" 60
echo "性能对比测试"
echo "=" 60
echo ""

# 测试本地部署
if curl -s http://127.0.0.1:28111/health > /dev/null 2>&1; then
    echo "✅ 本地服务运行中"
    test_transcription "http://127.0.0.1:28111" "本地部署"
else
    echo "⚠️  本地服务未运行"
    echo "   启动命令: ./start.sh"
    echo ""
fi

# 测试 Docker 部署
if docker ps | grep -q "typeless-backend"; then
    echo "✅ Docker 服务运行中"
    test_transcription "http://127.0.0.1:28111" "Docker 部署"
else
    echo "⚠️  Docker 服务未运行"
    echo "   启动命令: ./docker-start.sh"
    echo ""
fi

echo "=" 60
echo "📖 性能优化建议"
echo "=" 60
echo ""
echo "如果 Docker 性能明显慢于本地部署："
echo ""
echo "1. 查看性能指南:"
echo "   cat PERFORMANCE.md"
echo ""
echo "2. 移除资源限制:"
echo "   nano docker-compose.yml"
echo "   # 删除 deploy.resources 部分"
echo ""
echo "3. 重启 Docker 服务:"
echo "   ./docker-stop.sh"
echo "   ./docker-start.sh"
echo ""
echo "4. 或者使用本地部署（推荐）："
echo "   ./stop.sh          # 停止 Docker"
echo "   ./start.sh         # 启动本地服务"
echo ""
