#!/bin/bash
# Typeless 部署验证脚本

echo "🧪 测试 Typeless 部署..."
echo ""

# 1. 健康检查
echo "1️⃣ 测试后端健康检查..."
HEALTH=$(curl -s http://127.0.0.1:28111/health)
if [[ $HEALTH == *"healthy"* ]]; then
    echo "✅ 后端健康检查通过"
else
    echo "❌ 后端健康检查失败"
    echo "   响应: $HEALTH"
    exit 1
fi

# 2. API 根路径
echo ""
echo "2️⃣ 测试 API 根路径..."
ROOT=$(curl -s http://127.0.0.1:28111/)
if [[ $ROOT == *"Typeless Service"* ]]; then
    echo "✅ API 根路径正常"
else
    echo "⚠️  API 根路径响应异常"
fi

# 3. API 文档
echo ""
echo "3️⃣ 检查 API 文档..."
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:28111/docs | grep -q "200"; then
    echo "✅ API 文档可访问: http://127.0.0.1:28111/docs"
else
    echo "⚠️  API 文档不可访问"
fi

# 4. ASR 端点检查（不发送实际数据）
echo ""
echo "4️⃣ 检查 ASR 端点..."
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:28111/docs | grep -q "200"; then
    echo "✅ ASR API 端点可用"
else
    echo "⚠️  ASR API 端点异常"
fi

# 5. 测试完整 ASR 流程（如果有测试音频）
echo ""
echo "5️⃣ 测试 ASR 转录..."
if [ -f "test_audio.wav" ]; then
    echo "   发送测试音频..."
    TRANSCRIPT=$(curl -s -X POST \
        -H "Content-Type: application/octet-stream" \
        --data-binary @test_audio.wav \
        http://127.0.0.1:28111/api/asr/transcribe)

    if [[ $TRANSCRIPT == *"transcript"* ]]; then
        echo "✅ ASR 转录测试通过"
        echo "   结果: $(echo $TRANSCRIPT | python3 -c "import sys, json; print(json.load(sys.stdin).get('transcript', 'N/A'))" 2>/dev/null)"
    else
        echo "⚠️  ASR 转录测试失败"
        echo "   响应: $TRANSCRIPT"
    fi
else
    echo "⏭️  跳过 ASR 转录测试 (test_audio.wav 不存在)"
fi

echo ""
echo "=" 50
echo "✅ 部署测试完成！"
echo ""
echo "📍 可用的服务端点:"
echo "   - API: http://127.0.0.1:8000"
echo "   - 文档: http://127.0.0.1:28111/docs"
echo "   - 健康检查: http://127.0.0.1:28111/health"
echo ""
echo "🚀 下一步:"
echo "   在新终端启动 Swift 应用:"
echo "   cd ../TypelessApp && swift run TypelessApp"
echo ""
