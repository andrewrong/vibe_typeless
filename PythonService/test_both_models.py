"""测试 Whisper 和 VibeVoice 都能正常工作"""
import logging
logging.basicConfig(level=logging.ERROR)

print("=" * 60)
print("模型切换验证")
print("=" * 60)

# 测试 Whisper
print("\n1️⃣ 测试 Whisper...")
import sys
sys.path.insert(0, 'src')

# 临时修改 MODEL_TYPE
import src.asr as asr_module
original_type = asr_module.MODEL_TYPE
asr_module.MODEL_TYPE = "whisper"

from src.asr import get_asr_model
model = get_asr_model()
print(f"   ✅ Whisper 加载成功: {type(model).__name__}")

# 测试转录
import numpy as np
audio = np.zeros(16000, dtype=np.int16)
text = model.transcribe(audio, language='zh')
print(f"   ✅ Whisper 转录成功")

# 测试 VibeVoice
print("\n2️⃣ 测试 VibeVoice...")
asr_module.MODEL_TYPE = "vibevoice"

# 重新导入以刷新
import importlib
importlib.reload(asr_module)
from src.asr import get_asr_model as get_model2

model2 = get_model2()
print(f"   ✅ VibeVoice 加载成功: {type(model2).__name__}")

# 测试转录
audio2 = np.random.randint(-5000, 5000, 16000, dtype=np.int16)
text2 = model2.transcribe(audio2, language='zh')
print(f"   ✅ VibeVoice 转录成功")
print(f"   结果: {repr(text2)}")

# 恢复原始设置
asr_module.MODEL_TYPE = original_type

print("\n" + "=" * 60)
print("✅ 两个模型都正常工作！")
print("=" * 60)
print(f"\n当前默认模型: {asr_module.MODEL_TYPE}")
print(f"要切换模型，编辑 src/asr/__init__.py 中的 MODEL_TYPE")
