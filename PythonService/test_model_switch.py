"""
测试模型切换功能
"""
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

print("=" * 60)
print("ASR 模型切换测试")
print("=" * 60)

# 测试 1: 检查当前模型类型
print("\n1️⃣ 检查当前模型配置...")
from src.asr import MODEL_TYPE
print(f"   当前配置: MODEL_TYPE = '{MODEL_TYPE}'")

# 测试 2: 尝试加载模型
print(f"\n2️⃣ 尝试加载 {MODEL_TYPE.upper()} 模型...")
try:
    from src.asr import get_asr_model
    model = get_asr_model()
    print(f"   ✅ 模型加载成功")
    print(f"   类型: {type(model).__name__}")
    print(f"   模块: {type(model).__module__}")
except Exception as e:
    print(f"   ❌ 模型加载失败: {e}")
    sys.exit(1)

# 测试 3: 测试转录（使用静音数据）
print(f"\n3️⃣ 测试转录功能...")
import numpy as np

# 创建 1 秒的测试音频（16000 采样点，int16）
test_audio = np.zeros(16000, dtype=np.int16)

try:
    text = model.transcribe(test_audio, language="zh")
    print(f"   ✅ 转录功能正常")
    print(f"   结果: '{text}' (空音频应该返回空字符串)")
except Exception as e:
    print(f"   ❌ 转录失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 4: 检查模型属性
print(f"\n4️⃣ 模型信息...")
if hasattr(model, 'MODEL_ID'):
    print(f"   模型 ID: {model.MODEL_ID}")
if hasattr(model, 'MODEL_SIZES'):
    print(f"   可用大小: {model.MODEL_SIZES}")
if hasattr(model, 'config'):
    print(f"   配置: {model.config}")

print("\n" + "=" * 60)
print("✅ 所有测试通过！")
print("=" * 60)

print(f"\n当前使用的模型: {type(model).__name__}")
print(f"要切换模型，请编辑 src/asr/__init__.py 并修改 MODEL_TYPE")
