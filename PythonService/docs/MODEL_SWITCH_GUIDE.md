# 模型切换指南

## 快速切换到 VibeVoice

### 步骤 1：安装依赖

```bash
uv add mlx-audio
```

### 步骤 2：切换模型

编辑 `src/asr/__init__.py`，将第 13 行改为：

```python
MODEL_TYPE: Literal["whisper", "vibevoice"] = "vibevoice"
```

### 步骤 3：重启后端

```bash
# 停止当前后端
pkill -f uvicorn

# 重启后端
uv run uvicorn src.api.server:app --host 0.0.0.0 --port 8000
```

## 模型对比

| 特性 | Whisper (当前) | VibeVoice |
|------|---------------|-----------|
| 参数量 | 1.5B (large-v3) | 9B |
| 量化 | 4-bit | 8-bit |
| 速度 | 快 | 中等 |
| 精度 | 良好 | 更好 |
| 语言支持 | 99+ 语言 | 多语言 |
| 说话人分离 | ❌ | ✅ |
| 内存占用 | ~2GB | ~4GB |

## 切换回 Whisper

编辑 `src/asr/__init__.py`，将第 13 行改回：

```python
MODEL_TYPE: Literal["whisper", "vibevoice"] = "whisper"
```

然后重启后端。

## 故障排查

### 问题：ImportError: No module named 'mlx_audio'

**解决方案：**
```bash
uv add mlx-audio
```

### 问题：VibeVoice 下载失败

**解决方案：**
VibeVoice 模型会自动从 Hugging Face 下载。如果下载失败，请检查：
1. 网络连接
2. Hugging Face 访问权限
3. 磁盘空间（至少 5GB）

### 问题：内存不足

**解决方案：**
VibeVoice 需要约 4GB 内存。如果内存不足：
1. 关闭其他应用
2. 切换回 Whisper（只需要 2GB）

## 测试

测试模型是否正常工作：

```python
from src.asr import get_asr_model
import numpy as np

# 获取模型
model = get_asr_model()

# 创建测试音频（1秒静音）
audio = np.zeros(16000, dtype=np.int16)

# 测试转录
text = model.transcribe(audio, language="zh")
print(f"Model loaded: {type(model).__name__}")
```
