"""
完整的 ASR 流程测试
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000/api/asr"

print("=" * 60)
print("完整 ASR 测试")
print("=" * 60)

# 1. 开始会话
print("\n1️⃣ 开始会话...")
response = requests.post(f"{BASE_URL}/start", json={
    "app_info": "TestApp|com.test.app"
})
session_id = response.json()["session_id"]
print(f"   Session ID: {session_id}")

# 2. 模拟发送一些音频数据（使用真实音频文件）
print("\n2️⃣ 发送音频...")

# 使用现有的测试音频文件
import os
test_audio = "/Volumes/nomoshen_macmini/data/project/self/typeless_2/PythonService/test_long_audio.wav"

if os.path.exists(test_audio):
    with open(test_audio, "rb") as f:
        audio_data = f.read()

    # 发送音频
    response = requests.post(
        f"{BASE_URL}/audio/{session_id}",
        data=audio_data,
        headers={"Content-Type": "application/octet-stream"}
    )
    print(f"   音频发送成功")

    # 3. 停止会话
    print("\n3️⃣ 停止会话并获取转录...")
    response = requests.post(f"{BASE_URL}/stop/{session_id}")
    result = response.json()

    print(f"\n📝 最终转录结果:")
    print(f"   {result['final_transcript']!r}")

    if result['final_transcript']:
        print(f"\n✅ 转录成功！")
        print(f"   字符数: {len(result['final_transcript'])}")
    else:
        print(f"\n❌ 转录为空")
else:
    print(f"   ⚠️ 测试音频文件不存在: {test_audio}")

print("\n" + "=" * 60)
