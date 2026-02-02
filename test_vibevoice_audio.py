"""测试 VibeVoice 转录实际音频"""
import sys
sys.path.insert(0, 'src')

from src.asr import get_asr_model
import logging
import wave

logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("VibeVoice 真实音频测试")
print("=" * 60)

model = get_asr_model()
print(f"✅ 模型类型: {type(model).__name__}")

# 使用测试音频文件
import os
if os.path.exists('test_long_audio.wav'):
    print(f"\n1️⃣ 读取测试音频...")
    with wave.open('test_long_audio.wav', 'rb') as wav:
        frames = wav.getnframes()
        audio_data = wav.readframes(frames)
        audio_array = __import__('numpy').frombuffer(audio_data, dtype=__import__('numpy').int16)
    
    print(f"   音频: {len(audio_array)} 采样点 ({len(audio_array)/16000:.2f}秒)")
    print(f"   范围: [{audio_array.min()}, {audio_array.max()}]")
    
    print(f"\n2️⃣ 开始转录...")
    text = model.transcribe(audio_array, language='zh')
    
    print(f"\n3️⃣ 转录结果:")
    print(f"   长度: {len(text)} 字符")
    print(f"   内容: {repr(text)}")
    
    # 尝试解析 JSON
    if text.startswith('['):
        import json
        try:
            segments = json.loads(text)
            print(f"\n4️⃣ 解析后的片段:")
            for seg in segments:
                print(f"   - 说话人 {seg.get('Speaker')}: {seg.get('Content')}")
        except:
            print(f"   JSON 解析失败")
else:
    print("❌ 测试音频文件不存在")

print("\n" + "=" * 60)
