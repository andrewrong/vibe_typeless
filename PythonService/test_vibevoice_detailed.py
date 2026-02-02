"""
VibeVoice 详细测试
"""
import sys
import numpy as np
import tempfile
import logging

logging.basicConfig(level=logging.DEBUG)

print("=" * 60)
print("VibeVoice 详细转录测试")
print("=" * 60)

# 1. 创建测试音频
print("\n1️⃣ 创建测试音频...")
test_audio = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
print(f"   音频形状: {test_audio.shape}")
print(f"   音频范围: [{test_audio.min()}, {test_audio.max()}]")

# 2. 保存为 WAV 文件
print("\n2️⃣ 保存为 WAV 文件...")
import wave
fd, wav_path = tempfile.mkstemp(suffix=".wav")

try:
    with wave.open(wav_path, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(test_audio.tobytes())

    print(f"   ✅ 文件已保存: {wav_path}")

    # 3. 测试 generate_transcription
    print("\n3️⃣ 测试 generate_transcription...")

    from mlx_audio.stt.generate import generate_transcription

    result = generate_transcription(
        model="mlx-community/VibeVoice-ASR-8bit",
        audio_path=wav_path,
        format="text",
        verbose=True
    )

    print(f"\n   结果类型: {type(result)}")
    print(f"   结果: {result}")

except Exception as e:
    print(f"\n   ❌ 错误: {e}")
    import traceback
    traceback.print_exc()
finally:
    import os
    try:
        os.close(fd)
    except:
        pass
    try:
        os.unlink(wav_path)
    except:
        pass

print("\n" + "=" * 60)
