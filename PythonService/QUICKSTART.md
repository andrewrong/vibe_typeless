# Typeless Quick Start Guide

## 快速开始

### 1. 启动服务器

```bash
cd PythonService
PYTHONPATH=src uv run python -m api.server
```

服务器将在 http://127.0.0.1:8000 启动

### 2. 测试 API

#### 健康检查
```bash
curl http://127.0.0.1:8000/health
```

#### 转录音频文件
```bash
curl -X POST http://127.0.0.1:8000/api/asr/transcribe \
  --data-binary "@recording.wav" \
  -H "Content-Type: application/octet-stream"
```

#### 上传并处理音频（带后处理）
```bash
curl -X POST http://127.0.0.1:8000/api/postprocess/upload \
  -F "file=@meeting.mp3" \
  -F "apply_postprocess=true" \
  -F "remove_silence=true"
```

#### 文本后处理
```bash
curl -X POST http://127.0.0.1:8000/api/postprocess/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "um hello uh this is a test",
    "use_cloud_llm": false
  }'
```

### 3. Python 客户端示例

```python
import httpx

class TypelessClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.Client()

    def transcribe_file(self, file_path: str) -> str:
        """转录音频文件"""
        with open(file_path, "rb") as f:
            response = self.client.post(
                f"{self.base_url}/api/asr/transcribe",
                content=f.read(),
                headers={"Content-Type": "application/octet-stream"}
            )
        return response.json()["transcript"]

    def process_text(self, text: str, use_llm: bool = False) -> dict:
        """处理文本"""
        response = self.client.post(
            f"{self.base_url}/api/postprocess/text",
            json={"text": text, "use_cloud_llm": use_llm}
        )
        return response.json()

# 使用示例
client = TypelessClient()

# 转录音频
transcript = client.transcribe_file("recording.wav")
print(f"转录结果: {transcript}")

# 清理文本
result = client.process_text("um like hello everyone uh")
print(f"清理后: {result['processed']}")
```

### 4. 交互式文档

访问 http://127.0.0.1:8000/docs 查看 Swagger UI 交互式文档

## 当前状态

- ✅ **ASR 引擎**: MLX Whisper (base 模型，74M 参数)
- ✅ **测试**: 85/85 通过
- ✅ **服务器**: 运行中
- ✅ **文档**: 完整

## 模型信息

- **模型**: mlx-community/whisper-base-mlx
- **下载大小**: ~150MB (首次使用时自动下载)
- **语言**: 99+ 种语言自动检测
- **优化**: Apple Silicon (M1/M2/M3) 原生支持
- **量化**: fp16 (内存优化)

## API 端点

### ASR (语音识别)
- `POST /api/asr/start` - 启动转录会话
- `POST /api/asr/audio/{id}` - 发送音频块
- `POST /api/asr/stop/{id}` - 停止并获取结果
- `GET /api/asr/status/{id}` - 查询会话状态
- `POST /api/asr/transcribe` - 转录完整音频

### 后处理
- `POST /api/postprocess/text` - 文本清理
- `POST /api/postprocess/config` - 更新配置
- `GET /api/postprocess/config` - 查询配置
- `GET /api/postprocess/status` - 服务状态
- `POST /api/postprocess/upload` - 上传并处理音频文件

## 下一步

1. **测试真实音频** - 准备一些测试音频文件
2. **调整模型大小** - 根据性能需求选择 tiny/base/small/medium/large
3. **配置后处理** - 添加自定义填充词或规则
4. **性能测试** - 测量转录速度和准确率

## 故障排除

### 模型下载慢？
- 首次使用会自动从 HuggingFace 下载模型
- 模型会缓存到本地，后续使用无需重新下载
- 可以设置 `HF_ENDPOINT` 环境变量使用镜像站

### 内存不足？
- 使用更小的模型（tiny 而不是 base）
- 减少并发请求数
- 关闭其他应用释放内存

### 转录质量不理想？
- 确保音频质量良好（16kHz 采样率）
- 尝试更大的模型（small 或 medium）
- 添加特定语言参数
- 启用后处理清理填充词

## 更多信息

- **完整 API 文档**: [docs/API.md](docs/API.md)
- **ASR 决策文档**: [docs/ASR_DECISION.md](docs/ASR_DECISION.md)
- **集成指南**: [docs/WHISPER_INTEGRATION_COMPLETE.md](docs/WHISPER_INTEGRATION_COMPLETE.md)
- **进度追踪**: [PROGRESS.md](PROGRESS.md)
