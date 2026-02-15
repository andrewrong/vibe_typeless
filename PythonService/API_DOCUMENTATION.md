# Typeless Service API 文档

## 概述

Typeless Service 是一个高性能的语音识别（ASR）服务，支持实时流式转录和文件转录。当前使用 **SenseVoice Small** 模型，提供极速中文语音识别。

## 服务信息

- **版本**: 0.2.0
- **基础 URL**: `http://127.0.0.1:28111`
- **API 文档**: `http://127.0.0.1:28111/docs` (Swagger UI)
- **OpenAPI**: `http://127.0.0.1:28111/openapi.json`

## 核心特性

- ⚡ **极速识别**: SenseVoice 模型，70ms/10s 音频
- 🎯 **高准确率**: >95% 中文识别准确率
- 🌏 **多语言**: 支持中/英/日/韩/粤
- 💾 **低资源**: 228MB 模型，~1GB 内存
- 🔴 **实时流式**: WebSocket 支持实时预览

---

## API 端点

### 1. 健康检查

#### GET /health
检查服务状态。

**响应示例**:
```json
{
  "status": "healthy"
}
```

---

### 2. ASR 会话管理

#### POST /api/asr/start
开始新的录音会话。

**请求体**:
```json
{
  "app_info": "可选的应用信息，例如: com.apple.TextEdit"
}
```

**响应示例**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started"
}
```

---

#### POST /api/asr/audio/{session_id}
发送音频数据块（实时流式）。

**路径参数**:
- `session_id`: 会话 ID（从 start 接口获得）

**请求体**:
- Content-Type: `application/octet-stream`
- 数据: PCM 16-bit 音频字节流

**响应示例**:
```json
{
  "partial_transcript": "",
  "is_final": false
}
```

---

#### POST /api/asr/stop/{session_id}
停止会话并获取最终转录结果。

**路径参数**:
- `session_id`: 会话 ID

**响应示例**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "stopped",
  "final_transcript": "这是识别的文本内容",
  "total_chunks": 42
}
```

---

#### GET /api/asr/preview/{session_id}
获取实时转录预览。

**路径参数**:
- `session_id`: 会话 ID

**响应示例**:
```json
{
  "partial_transcript": "实时预览的文本",
  "is_final": false
}
```

---

### 3. 模型配置

#### GET /api/asr/config
获取当前模型配置。

**响应示例**:
```json
{
  "current_model": "sensevoice-small",
  "language": "",
  "fp16": true,
  "available_models": [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
    "sensevoice"
  ]
}
```

---

#### POST /api/asr/config
更新模型配置（需要重启服务生效）。

**请求体**:
```json
{
  "model_size": "sensevoice",
  "language": "zh",
  "fp16": true
}
```

**响应示例**:
```json
{
  "current_model": "sensevoice-small",
  "language": "zh",
  "fp16": true,
  "available_models": ["tiny", "base", "small", "medium", "large-v3", "sensevoice"]
}
```

---

### 4. 文件转录

#### POST /api/postprocess/upload
**上传音频文件进行整体转录（推荐用于 ≤ 30 秒的音频）**。

**特点**: 整个音频直接转录，不切割分段，结果自然流畅，适合短视频/语音消息。

**请求体**:
- Content-Type: `multipart/form-data`
- 字段:
  - `file`: 音频文件 (wav, mp3, m4a, flac, ogg, aac)
  - `language`: 语言代码 (可选，默认 "zh")
  - `apply_postprocess`: 是否应用后处理 (可选，默认 true)

**响应示例**:
```json
{
  "filename": "recording.wav",
  "success": true,
  "transcript": "识别的文本内容",
  "duration": 10.5,
  "processing_stats": {
    "segments": 1,
    "silence_removed": 0.5
  }
}
```

**响应示例**:
```json
{
  "transcript": "你能听到我在说话吗？我感觉你这个翻译有点问题。",
  "processed_transcript": "你能听到我在说话吗？我感觉你这个翻译有点问题。",
  "audio_metadata": {
    "duration": 3.734,
    "sample_rate": 16000
  },
  "processing_stats": {
    "postprocess_stats": {
      "fillers_removed": 0,
      "duplicates_removed": 0
    }
  }
}
```

---

#### POST /api/postprocess/upload-long
**上传长音频文件（> 30 秒），先分段再转录**。

⚠️ **注意**: 此接口会将音频切成小段分别转录，可能导致句子断裂。如需自然流畅的结果，建议使用 `/upload` 接口。

**Content-Type**: `multipart/form-data`

**请求参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file` | File | ✅ | - | 音频文件 (WAV, MP3, M4A, FLAC, OGG, AAC) |
| `apply_postprocess` | bool | ❌ | `true` | 是否应用后处理 |
| `language` | string | ❌ | `zh` | 语言代码: `zh` / `en` / `ja` / `ko` / `yue` / `auto` |

**语言代码说明**:
- `zh`: 中文（默认）
- `en`: 英文
- `ja`: 日语
- `ko`: 韩语
- `yue`: 粤语
- `auto`: 自动检测（可能误判噪音为日语）

**响应示例**:
```json
{
  "transcript": "完整转录文本...",
  "processed_transcript": "处理后的文本（带标点）...",
  "audio_metadata": {
    "duration": 120.5,
    "sample_rate": 16000,
    "num_segments": 5,
    "strategy": "hybrid"
  },
  "processing_stats": {
    "num_segments": 5,
    "strategy": "hybrid",
    "merge_strategy": "smart",
    "postprocess_stats": {
      "chars_added": 10
    }
  },
  "segments": [
    {"segment_index": 0, "duration": 24.0},
    {"segment_index": 1, "duration": 25.5}
  ]
}
```

**📌 如何选择？**

| 场景 | 推荐接口 | 原因 |
|------|---------|------|
| 短视频/语音消息 (≤30秒) | **`/upload`** ✅ | 整体转录，句子自然流畅 |
| 长音频 (>30秒) | `/upload-long` | 分段处理，避免内存问题 |
| 需要自然语句 | **`/upload`** ✅ | 不切分，保持语义完整 |
| 实时性要求高 | **`/upload`** ✅ | 处理更快，无分段开销 |

⚠️ **警告**: `/upload-long` 会把音频切成 **0.5秒~30秒** 的小段分别转录，结果可能是：
- "你能听。那我再说。我。感觉你在。反正有。有问题。" ❌

而 `/upload` 返回：
- "你能听到我在说话吗？我感觉你这个翻译有点问题。" ✅
| 智能合并 | 否 | ✅ 是 |
| 处理时间 | 快 (~0.5s) | 较慢 (分段数 × 0.5s) |

**使用示例**（仅用于 >30秒的长音频）：
```python
import requests

url = "http://127.0.0.1:28111/api/postprocess/upload-long"

with open("5_minutes_meeting.mp3", "rb") as f:
    files = {"file": f}
    data = {
        "apply_postprocess": "true",
        "language": "zh"
    }

    response = requests.post(url, files=files, data=data, timeout=120)
    result = response.json()

print(f"转录: {result['transcript']}")
# 注意：结果可能是不连贯的短句拼接
```

**💡 推荐：语音消息用 `/upload` 接口**
```python
import requests

url = "http://127.0.0.1:28111/api/postprocess/upload"

with open("voice_message.ogg", "rb") as f:
    files = {"file": f}
    data = {
        "language": "zh",
        "apply_postprocess": "true"
    }
    response = requests.post(url, files=files, data=data)
    result = response.json()
    print(f"转录: {result['transcript']}")  # 自然流畅的句子
```

**超时建议**:
- 1-2 分钟: 30 秒超时
- 3-5 分钟: 60 秒超时
- 5-10 分钟: 120 秒超时

---

### 5. 后处理

#### POST /api/postprocess/text
对文本进行后处理（标点、格式化）。

**请求体**:
```json
{
  "text": "需要处理的文本",
  "operations": ["punctuation", "formatting", "filler_removal"]
}
```

**响应示例**:
```json
{
  "processed_text": "处理后的文本。",
  "operations_applied": ["punctuation", "formatting"],
  "stats": {
    "chars_added": 1,
    "fillers_removed": 2
  }
}
```

---

#### GET /api/postprocess/status
获取后处理服务状态。

**响应示例**:
```json
{
  "status": "running",
  "capabilities": {
    "rule_based": true,
    "cloud_llm": true,
    "providers": ["claude", "openai"],
    "features": [
      "filler_removal",
      "duplicate_removal",
      "self_correction",
      "auto_formatting"
    ]
  }
}
```

---

## 使用示例

### 完整录音流程

```python
import requests
import time

BASE_URL = "http://127.0.0.1:28111"

# 1. 开始会话
response = requests.post(f"{BASE_URL}/api/asr/start",
    json={"app_info": "com.example.MyApp"})
session_id = response.json()["session_id"]
print(f"会话开始: {session_id}")

# 2. 发送音频（循环发送音频块）
audio_chunk = b"..."  # PCM 16-bit 音频数据
requests.post(f"{BASE_URL}/api/asr/audio/{session_id}",
    data=audio_chunk,
    headers={"Content-Type": "application/octet-stream"})

# 3. 停止并获取结果
response = requests.post(f"{BASE_URL}/api/asr/stop/{session_id}")
result = response.json()
print(f"转录结果: {result['final_transcript']}")
```

---

### 文件转录

```python
import requests

BASE_URL = "http://127.0.0.1:28111"

with open("recording.wav", "rb") as f:
    files = {"file": f}
    data = {"language": "zh", "apply_postprocess": "true"}

    response = requests.post(f"{BASE_URL}/api/postprocess/upload",
        files=files, data=data)

    result = response.json()
    print(f"转录结果: {result['transcript']}")
```

---

### 使用 cURL

```bash
# 开始会话
curl -X POST http://127.0.0.1:28111/api/asr/start \
  -H "Content-Type: application/json" \
  -d '{"app_info": "test"}'

# 上传文件转录
curl -X POST http://127.0.0.1:28111/api/postprocess/upload \
  -F "file=@recording.wav" \
  -F "language=zh"
```

---

## 音频格式要求

- **采样率**: 16000 Hz (推荐)
- **位深度**: 16-bit PCM
- **声道**: 单声道
- **格式**: WAV, MP3, M4A, FLAC, OGG, AAC (文件上传)

---

## 性能指标

| 指标 | 数值 |
|------|------|
| **模型大小** | 228 MB |
| **内存占用** | ~1 GB |
| **加载时间** | ~0.5s |
| **转录速度** | ~70ms / 10s 音频 |
| **实时倍率** | 70x+ |
| **中文准确率** | >95% |

---

## 错误处理

### HTTP 状态码

- `200`: 成功
- `404`: 会话不存在
- `422`: 请求参数错误
- `500`: 服务器内部错误

### 错误响应示例

```json
{
  "detail": "Session not found"
}
```

---

## 模型对比

| 特性 | SenseVoice | Whisper |
|------|------------|---------|
| **大小** | 228MB | 3GB |
| **速度** | 70ms | 1-2s |
| **中文** | 优秀 | 良好 |
| **内存** | ~1GB | ~4GB |
| **语言** | 中/英/日/韩/粤 | 99种 |

---

## 配置说明

### 环境变量 (.env)

```bash
# AI 后处理（默认关闭）
ENABLE_AI_POSTPROCESS=false

# AI 提供商（如需开启）
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here
```

### 切换模型

编辑 `src/asr/__init__.py`:
```python
MODEL_TYPE = "sensevoice"  # 或 "whisper", "vibevoice"
```

---

## 许可证

本项目遵循开源许可证。详见项目仓库。

---

## 联系方式

- **GitHub**: https://github.com/andrewrong/vibe_typeless
- **版本**: v0.2.0-sensevoice
