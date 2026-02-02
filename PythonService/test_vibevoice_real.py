"""
测试 VibeVoice 是否正常工作
"""
import sys
sys.path.insert(0, 'src')

from src.asr import get_asr_model
import logging

logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("VibeVoice 测试")
print("=" * 60)

# 获取模型
print("\n1️⃣ 加载 VibeVoice 模型...")
model = get_asr_model()
print(f"   ✅ 模型类型: {type(model).__name__}")

# 测试转录
print("\n2️⃣ 测试转录功能...")
import numpy as np

# 创建测试音频（随机噪声）
audio = np.random.randint(-10000, 10000, 16000, dtype=np.int16)
print(f"   测试音频: {len(audio)} 采样点 (1秒)")

# 转录
print("\n   开始转录...")
text = model.transcribe(audio, language='zh')

print(f"\n3️⃣ 转录结果:")
print(f"   文本: {repr(text)}")
print(f"   长度: {len(text)} 字符")

print("\n" + "=" * 60)
print("✅ VibeVoice 测试完成！")
print("=" * 60)
print("\n您现在可以：")
print("1. 使用 Swift 应用测试（按下 Right Control 录音）")
print("2. 使用 API 测试：")
print("   curl -X POST http://localhost:8000/api/asr/start \\")
print("     -H 'Content-Type: application/json' \\")
print("     -d '{\"app_info\":\"TestApp|com.test.app\"}'")
