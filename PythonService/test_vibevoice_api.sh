#!/bin/bash
# VibeVoice API 测试脚本

echo "================================"
echo "VibeVoice API 测试"
echo "================================"

# 1. 启动会话
echo -e "\n1️⃣ 启动 ASR 会话..."
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8000/api/asr/start \
  -H "Content-Type: application/json" \
  -d '{"app_info":"TestApp|com.test.app"}')

echo "会话响应: $SESSION_RESPONSE"

SESSION_ID=$(echo $SESSION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', ''))" 2>/dev/null)

if [ -z "$SESSION_ID" ]; then
  echo "❌ 获取 session_id 失败"
  exit 1
fi

echo "✅ Session ID: $SESSION_ID"

# 2. 发送测试音频
echo -e "\n2️⃣ 发送测试音频..."
if [ -f "test_long_audio.wav" ]; then
  curl -s -X POST "http://localhost:8000/api/asr/audio/$SESSION_ID" \
    -H "Content-Type: application/octet-stream" \
    --data-binary @test_long_audio.wav \
    > /dev/null
  echo "✅ 音频已发送"
else
  echo "⚠️  测试音频文件不存在，跳过"
fi

# 3. 停止会话并获取结果
echo -e "\n3️⃣ 停止会话并获取转录..."
RESULT=$(curl -s -X POST "http://localhost:8000/api/asr/stop/$SESSION_ID")

echo "转录结果:"
echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"

echo -e "\n================================"
echo "✅ 测试完成"
echo "================================"
