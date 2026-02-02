"""
VibeVoice 诊断脚本
"""
import sys

print("=" * 60)
print("VibeVoice 诊断")
print("=" * 60)

# 1. 检查版本
print("\n1️⃣ 检查包版本...")
try:
    import mlx
    print(f"   ✅ mlx: {mlx.__version__ if hasattr(mlx, '__version__') else 'unknown'}")
except Exception as e:
    print(f"   ❌ mlx: {e}")

try:
    import mlx_audio
    print(f"   ✅ mlx-audio: {mlx_audio.__version__}")
except Exception as e:
    print(f"   ❌ mlx-audio: {e}")

try:
    import transformers
    print(f"   ✅ transformers: {transformers.__version__}")
except Exception as e:
    print(f"   ❌ transformers: {e}")

# 2. 测试模型加载
print("\n2️⃣ 测试 VibeVoice 模型加载...")
try:
    from mlx_audio.stt.utils import load_model
    model = load_model("mlx-community/VibeVoice-ASR-8bit")
    print(f"   ✅ 模型加载成功: {type(model)}")
except Exception as e:
    print(f"   ❌ 模型加载失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 检查模型配置
print("\n3️⃣ 检查 Hugging Face 模型配置...")
try:
    from huggingface_hub import hf_hub_download
    import json

    # 下载配置文件
    config_path = hf_hub_download(
        repo_id="mlx-community/VibeVoice-ASR-8bit",
        filename="config.json",
        local_dir="/tmp/vibevoice_check"
    )

    with open(config_path, 'r') as f:
        config = json.load(f)

    print(f"   ✅ 配置加载成功")
    print(f"   model_type: {config.get('model_type', 'N/A')}")
    print(f"   architecture: {config.get('architectures', 'N/A')}")
except Exception as e:
    print(f"   ❌ 配置加载失败: {e}")

print("\n" + "=" * 60)
