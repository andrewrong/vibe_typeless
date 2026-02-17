# Typeless Service API 文档

## 概述

Typeless Service 是一个高性能的语音识别（ASR）服务，支持实时流式转录和文件转录。当前使用 **SenseVoice Small** 模型，提供极速中文语音识别。

## 服务信息

- **版本**: 0.3.0
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
  - `language`: 语言代码 (可选，默认 "auto")
  - `postprocess_mode`: 后处理模式 (可选，默认 "standard")
    - `none`: 不做后处理（最快）
    - `basic`: 基础处理（去重复 + 标点）
    - `standard`: 标准处理（填充词移除、修正、格式化）
    - `advanced`: 高级处理（标准 + AI 增强，质量最高）

**响应示例**:
```json
{
  "transcript": "大年三十除夕我和女儿刘总在吉隆坡马来西亚过年",
  "processed_transcript": "大年三十除夕，我和女儿刘总在吉隆坡、马来西亚过年。",
  "audio_metadata": {
    "duration": 10.5,
    "sample_rate": 16000,
    "channels": 1,
    "bit_depth": 16
  },
  "processing_stats": {
    "postprocess_stats": {
      "fillers_removed": 2,
      "duplicates_removed": 0,
      "corrections_applied": 1,
      "total_changes": 3,
      "mode": "standard"
    }
  },
  "silence_regions": null
}
```

**AI 增强模式示例** (`postprocess_mode=advanced`):
```json
{
  "transcript": "天是大年3十除夕我和女儿刘总在吉隆坡马来西亚过年",
  "processed_transcript": "大年三十除夕，我和女儿刘总在吉隆坡、马来西亚过年。我们和女儿的朋友 Elda 一家一起过年，孩子们玩得很开心。",
  "processing_stats": {
    "postprocess_stats": {
      "mode": "advanced",
      "ai_enhanced": true,
      "ai_provider": "openai",
      "ai_model": "gpt-4o-mini"
    }
  }
}
```

**后处理模式对比**:

| 模式 | 速度 | 处理内容 | 适用场景 |
|------|------|----------|----------|
| `none` | ⚡ 最快 | 不做任何处理 | 实时性要求最高 |
| `basic` | 🚀 快 | 去重复词 + 标点修正 | 轻度处理 |
| `standard` | ✅ 推荐 | 填充词移除 + 去重 + 修正 + 格式化 | 日常使用（默认） |
| `advanced` | 🐢 较慢 | Standard + AI 增强润色 | 高质量文档输出 |

---

#### POST /api/postprocess/upload-long
**上传长音频文件（> 30 秒），智能分段转录**。

**特点**: 使用 VAD + 智能分段，在说话停顿处切割，保持句子完整性。支持参数化后处理。

**Content-Type**: `multipart/form-data`

**请求参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file` | File | ✅ | - | 音频文件 (WAV, MP3, M4A, FLAC, OGG, AAC) |
| `postprocess_mode` | string | ❌ | `standard` | 后处理模式: `none` / `basic` / `standard` / `advanced` |
| `language` | string | ❌ | `auto` | 语言代码: `zh` / `en` / `ja` / `ko` / `yue` / `auto` |

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
  "transcript": "大年三十除夕我和女儿刘总在吉隆坡马来西亚过年我老婆回国了...",
  "processed_transcript": "大年三十除夕，我和女儿刘总在吉隆坡、马来西亚过年。我老婆回国了，所以只有我们两个。...",
  "audio_metadata": {
    "duration": 115.734,
    "sample_rate": 16000,
    "channels": 1,
    "bit_depth": 16
  },
  "processing_stats": {
    "num_segments": 7,
    "strategy": "audio_pipeline",
    "postprocess_stats": {
      "fillers_removed": 0,
      "duplicates_removed": 0,
      "corrections_applied": 0,
      "total_changes": 0,
      "mode": "standard"
    }
  },
  "segments": [
    {"segment_index": 0, "duration": 17.15},
    {"segment_index": 1, "duration": 18.15},
    {"segment_index": 2, "duration": 17.85},
    {"segment_index": 3, "duration": 18.45},
    {"segment_index": 4, "duration": 19.15},
    {"segment_index": 5, "duration": 18.5},
    {"segment_index": 6, "duration": 5.94}
  ]
}
```

**AI 增强模式示例** (`postprocess_mode=advanced`):
```json
{
  "transcript": "天是大年3十除夕我和女儿刘总在吉隆坡马来西亚过年...",
  "processed_transcript": "大年三十除夕，我和女儿刘总在吉隆坡、马来西亚过年。...\n\n宝贝玩得很开心，还吃了很多零食和糖果...",
  "processing_stats": {
    "num_segments": 7,
    "strategy": "audio_pipeline",
    "postprocess_stats": {
      "mode": "advanced",
      "ai_enhanced": true,
      "ai_provider": "openai",
      "ai_model": "gpt-4o-mini"
    }
  }
}
```

**📌 如何选择？**

| 场景 | 推荐接口 | 原因 |
|------|---------|------|
| 短视频/语音消息 (≤30秒) | **`/upload`** ✅ | 整体转录，句子自然流畅 |
| 长音频 (>30秒) | **`/upload-long`** ✅ | 智能分段，保持句子完整性 |
| 需要 AI 润色 | **`/upload-long` + advanced** ✅ | AI 增强，输出高质量文档 |
| 实时性要求高 | **`/upload`** ✅ | 处理更快 |

**智能分段说明**:
- 使用 VAD（语音活动检测）识别说话停顿
- 在能量低点（停顿处）切割，而非固定时长
- 目标段长：8-20 秒，平衡上下文与准确率
- 115 秒音频通常分成 6-8 个自然段落

**使用示例**:
```python
import requests

url = "http://127.0.0.1:28111/api/postprocess/upload-long"

# 标准模式（默认）
with open("meeting.mp3", "rb") as f:
    files = {"file": f}
    data = {
        "postprocess_mode": "standard",
        "language": "auto"
    }
    response = requests.post(url, files=files, data=data, timeout=120)
    result = response.json()
    print(f"转录: {result['transcript']}")
    print(f"处理后: {result['processed_transcript']}")

# AI 增强模式（高质量输出）
with open("interview.mp3", "rb") as f:
    files = {"file": f}
    data = {
        "postprocess_mode": "advanced",  # 启用 AI 增强
        "language": "auto"
    }
    response = requests.post(url, files=files, data=data, timeout=180)
    result = response.json()
    # AI 会润色文本、分段、优化可读性
    print(f"AI 处理后: {result['processed_transcript']}")
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
对文本进行后处理（支持 4 种处理模式）。

**请求体**:
```json
{
  "text": "需要处理的文本",
  "mode": "standard",
  "use_llm": false
}
```

**参数说明**:
- `text`: 需要处理的文本（必填）
- `mode`: 处理模式（可选，默认 `standard`）
  - `none`: 不做处理
  - `basic`: 基础处理（去重复 + 标点）
  - `standard`: 标准处理（填充词、修正、格式化）
  - `advanced`: 高级处理（需设置 `use_llm: true`）
- `use_llm`: 是否使用云端 LLM 增强（可选，默认 `false`）

**响应示例**:
```json
{
  "original": "需要处理的文本",
  "processed": "处理后的文本。",
  "stats": {
    "fillers_removed": 2,
    "duplicates_removed": 1,
    "corrections_applied": 0,
    "total_changes": 3,
    "mode": "standard"
  },
  "provider_used": "rules"
}
```

**AI 增强响应示例**:
```json
{
  "original": "大年三十我和女儿在吉隆坡过年",
  "processed": "大年三十，我和女儿在吉隆坡过年。我们一起吃年夜饭，玩得很开心。",
  "stats": {
    "mode": "advanced",
    "ai_enhanced": true
  },
  "provider_used": "openai"
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
    data = {"language": "zh", "postprocess_mode": "standard"}

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

# 上传文件转录（标准模式）
curl -X POST http://127.0.0.1:28111/api/postprocess/upload \
  -F "file=@recording.wav" \
  -F "language=zh" \
  -F "postprocess_mode=standard"

# 长音频 + AI 增强模式
curl -X POST http://127.0.0.1:28111/api/postprocess/upload-long \
  -F "file=@meeting.mp3" \
  -F "language=auto" \
  -F "postprocess_mode=advanced"
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

## 更新日志

### v0.3.0 (2026-02-17)
- ✨ **新增**: 参数化后处理模式 (`none` / `basic` / `standard` / `advanced`)
- ✨ **新增**: AI 增强模式（基于 OpenAI/Gemini/Ollama）
- ✨ **新增**: 智能音频分段（基于能量检测，在停顿处切割）
- 🔧 **优化**: `/upload` 和 `/upload-long` 接口统一参数
- 🔧 **优化**: 可复用的后处理函数

### v0.2.0 (之前版本)
- ✨ 集成 SenseVoice Small ASR 模型
- ✨ 支持实时流式 ASR
- ✨ 支持文件上传转录
- ✨ 基础后处理功能

---

## 许可证

本项目遵循开源许可证。详见项目仓库。

---

## 联系方式

- **GitHub**: https://github.com/andrewrong/vibe_typeless
- **版本**: v0.3.0
