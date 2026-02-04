# Typeless - macOS 本地语音转文字工具

基于 MLX Whisper 的本地 ASR 服务，配合 AI 文本后处理。

## 快速开始（本地部署）

> 💡 **推荐**：本地部署提供最佳性能（100% GPU 加速），适合开发和生产环境。

### 1. 安装依赖

```bash
cd PythonService

# 安装 uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv sync
```

### 2. 配置环境

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置，添加 API 密钥
nano .env  # 或使用其他编辑器
```

**必须配置以下之一：**
```bash
# OpenAI（推荐）
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# Google Gemini
AI_PROVIDER=gemini
GEMINI_API_KEY=your-key-here

# Ollama（本地免费）
AI_PROVIDER=ollama
```

### 3. 启动后端

```bash
./start.sh
```

### 4. 启动前端

```bash
# 新开一个终端
cd TypelessApp
swift run TypelessApp
```

### 5. 停止服务

```bash
cd PythonService
./stop.sh
```

## 📖 完整文档

- [本地部署指南](PythonService/LOCAL_DEPLOYMENT.md) - 详细的本地部署步骤
- [完整部署指南](PythonService/DEPLOYMENT.md) - 包含所有部署选项
- [性能优化指南](PythonService/PERFORMANCE.md) - 性能对比和优化建议

```bash
# 新开一个终端
cd TypelessApp
swift run TypelessApp
```

### 3. 停止服务

```bash
cd PythonService
./stop.sh
```

## 功能特性

- ✅ **本地语音识别**: MLX Whisper large-v3
- ✅ **AI 文本后处理**: 支持 OpenAI/Gemini/Ollama
- ✅ **长音频支持**: 自动分段处理
- ✅ **实时转录**: WebSocket 流式传输
- ✅ **说话人分离**: WhisperX 支持（可选）

## 系统要求

- **操作系统**: macOS 14+ (M 系列芯片推荐)
- **Python**: 3.10+
- **Swift**: 6.0+
- **内存**: 至少 8GB（推荐 16GB）

## 项目结构

```
typeless_2/
├── PythonService/          # Python 后端服务
│   ├── src/
│   │   ├── api/           # FastAPI 服务
│   │   ├── asr/           # Whisper ASR
│   │   └── ai/            # AI 后处理
│   ├── start.sh           # 启动脚本
│   ├── stop.sh            # 停止脚本
│   └── DEPLOYMENT.md      # 详细部署文档
└── TypelessApp/           # Swift 前端应用
    └── Sources/
        ├── App/           # 应用入口
        ├── Core/          # 核心模块
        ├── Services/      # API 服务
        └── Resources/     # 资源文件
```

## 配置说明

### 环境变量 (PythonService/.env)

```bash
# AI 提供商选择: openai, gemini, ollama
AI_PROVIDER=openai

# OpenAI 配置
OPENAI_API_KEY=sk-your-key-here

# 或使用 Google Gemini
# AI_PROVIDER=gemini
# GEMINI_API_KEY=your-key-here

# 或使用本地 Ollama
# AI_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
```

### Swift 应用配置

Swift 应用默认连接 `http://127.0.0.1:28111`，如需修改：

编辑 `TypelessApp/Sources/TypelessApp/Services/ASRService/ASRService.swift`:

```swift
init(baseURL: String = "http://127.0.0.1:28111") {
    // 修改为你的后端地址
}
```

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | API 信息 |
| `/health` | GET | 健康检查 |
| `/docs` | GET | API 文档 |
| `/api/asr/transcribe` | POST | 完整音频转录 |
| `/api/asr/start` | POST | 开始流式会话 |
| `/api/asr/audio/{session_id}` | POST | 发送音频块 |
| `/api/asr/stop/{session_id}` | POST | 结束会话 |
| `/api/ai/postprocess` | POST | AI 文本后处理 |

## 常见问题

### Q: 后端启动失败？
A: 检查端口是否被占用: `lsof -i :8000`

### Q: Swift 应用无法连接后端？
A: 确认后端已启动: `curl http://127.0.0.1:28111/health`

### Q: 模型下载很慢？
A: 首次运行会下载 ~3GB 模型，请耐心等待

### Q: 内存占用过高？
A: 可以在 `src/asr/model_config.py` 中改用更小的模型（如 `base` 或 `small`）

## 开发

### 运行测试

```bash
cd PythonService
uv run pytest

# 或测试特定文件
uv run pytest tests/test_asr.py
```

### 查看日志

```bash
# 后端日志
tail -f PythonService/runtime/logs/server.log
```

## 文档

- [部署指南](PythonService/DEPLOYMENT.md) - 详细部署说明
- [性能优化指南](PythonService/PERFORMANCE.md) - Docker vs 本地性能对比
- [Docker 部署](PythonService/DOCKER.md) - Docker 容器化部署
- [部署方式对比](PythonService/DEPLOYMENT_COMPARISON.md) - 本地 vs Docker 对比
- [Docker 部署](PythonService/DOCKER.md) - Docker 容器化部署
- [部署方式对比](PythonService/DEPLOYMENT_COMPARISON.md) - 本地 vs Docker 对比
- [部署检查清单](PythonService/CHECKLIST.md) - 部署验证清单
- [API 文档](http://127.0.0.1:28111/docs) - 交互式 API 文档（服务启动后）

## 版本信息

- **后端**: v0.2.0
- **前端**: v0.1.0
- **Whisper**: large-v3
- **MLX**: 最新版

## License

MIT

---

**Made with ❤️ on macOS**
