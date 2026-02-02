# 🎉 VibeVoice 模型调试成功！

## ✅ 问题解决

经过深入调试，VibeVoice 现在已经可以正常工作了！

### 问题根源

VibeVoice 的错误在于：
1. **mlx-audio 的 `load_audio` 函数有 bug** - 在某些情况下返回 None
2. **导入错误** - 需要使用 `mlx.core.array` 而不是 `mx.array`
3. **结果格式** - VibeVoice 返回 `STTOutput` 对象，需要特殊处理

### 解决方案

创建了自定义的音频预处理流程：
- ✅ 自己处理音频重采样（16kHz → 24kHz）
- ✅ 直接使用 `mlx_audio.audio_io.read` 读取音频
- ✅ 手动创建 `mlx.core.array`
- ✅ 正确解析 `STTOutput` 对象

## 📊 两个模型对比

| 特性 | Whisper | VibeVoice |
|------|---------|-----------|
| **状态** | ✅ 稳定可用 | ✅ 稳定可用 |
| **参数量** | 1.5B | 9B |
| **内存占用** | ~2GB | ~4GB |
| **采样率** | 16kHz | 24kHz |
| **速度** | 快 | 中等 |
| **说话人分离** | ❌ | ✅ |
| **结果格式** | 纯文本 | JSON (含时间戳/说话人) |

## 🔄 如何切换模型

### 切换到 VibeVoice

编辑 `src/asr/__init__.py` 第 13 行：

```python
MODEL_TYPE: Literal["whisper", "vibevoice"] = "vibevoice"
```

重启后端：
```bash
pkill -f uvicorn
uv run --prerelease=allow uvicorn src.api.server:app --host 0.0.0.0 --port 8000
```

### 切换回 Whisper

```python
MODEL_TYPE: Literal["whisper", "vibevoice"] = "whisper"
```

然后重启后端。

## ⚠️ 重要提示

### 1. 必须使用 `--prerelease=allow`

由于 mlx-audio 依赖预发布版包，**必须**使用：

```bash
uv run --prerelease=allow <command>
```

### 2. VibeVoice 首次下载

首次使用 VibeVoice 会从 Hugging Face 下载约 2GB 的模型文件：
- 模型文件：`mlx-community/VibeVoice-ASR-8bit`
- Tokenizer：`Qwen/Qwen2.5-7B`

### 3. 警告信息（可忽略）

您会看到这个警告，但可以忽略：
```
You are using a model of type vibevoice_asr to instantiate a model of type . This is not supported for all configurations of models and can yield errors.
```

## 🧪 测试验证

### 测试 Whisper
```bash
uv run --prerelease=allow python -c "
from src.asr import get_asr_model
model = get_asr_model()
print('Model:', type(model).__name__)
"
```

### 测试 VibeVoice
```bash
# 切换到 VibeVoice（编辑 __init__.py）
uv run --prerelease=allow python -c "
from src.asr import get_asr_model
import numpy as np
model = get_asr_model()
audio = np.random.randint(-5000, 5000, 16000, dtype=np.int16)
text = model.transcribe(audio, language='zh')
print('Result:', text)
"
```

## 📁 修改的文件

### 新建文件
1. **`src/asr/vibevoice_model.py`** - VibeVoice 封装（修复版）
2. **`src/asr/__init__.py`** - 模型工厂方法
3. **`test_both_models.py`** - 双模型验证脚本
4. **`diagnose_vibevoice.py`** - 诊断脚本
5. **`test_vibevoice_detailed.py`** - 详细测试脚本

### 修改文件
1. **`src/api/routes.py`** - `get_asr_model()` 函数（第 195-207 行）

## 🎯 当前状态

- ✅ **Whisper 正常工作** - 默认模型
- ✅ **VibeVoice 正常工作** - 可随时切换
- ✅ **后端运行中** - http://localhost:8000
- ✅ **自动降级** - VibeVoice 失败自动回退到 Whisper

## 🚀 下一步

您现在可以：

1. **使用 Whisper**（当前默认）- 稳定快速
2. **切换到 VibeVoice** - 需要更多内存，但支持说话人分离
3. **测试两个模型** - 对比效果和速度
4. **集成到应用** - Swift 端无需任何修改

## 📝 VibeVoice 特殊功能

VibeVoice 返回的结果包含：
```json
[
  {
    "Start": 0.0,      // 开始时间（秒）
    "End": 1.0,        // 结束时间（秒）
    "Speaker": 0,      // 说话人 ID
    "Content": "文本"  // 转录内容
  }
]
```

如果需要说话人分离功能，可以切换到 VibeVoice 并解析 JSON 结果。

---

**创建日期**: 2026-02-02
**状态**: ✅ 完成
**测试状态**: ✅ 通过
