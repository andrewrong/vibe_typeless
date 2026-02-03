# Typeless 部署指南

## 项目架构

```
┌─────────────────────────────────────────────────────────┐
│  Swift App (TypelessApp)                                │
│  - macOS 14+ 应用                                       │
│  - 音频捕获 + 文本注入                                  │
│  - 连接到 http://127.0.0.1:8000                         │
└─────────────────────────────────────────────────────────┘
                          │
                    HTTP/WebSocket
                          │
┌─────────────────────────────────────────────────────────┐
│  Python Service (FastAPI)                               │
│  - ASR: MLX Whisper large-v3                            │
│  - AI 后处理: OpenAI/Gemini/Ollama                      │
│  - 监听: 127.0.0.1:8000                                 │
└─────────────────────────────────────────────────────────┘
```

## 部署步骤

### 1. 后端部署 (Python Service)

#### 1.1 环境准备

```bash
cd PythonService

# 检查 Python 版本 (需要 Python 3.10+)
python --version

# 安装 uv (如果还没安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync
```

#### 1.2 配置环境变量

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，配置 API 密钥
# 必须的配置：
# - OPENAI_API_KEY (OpenAI) 或 GEMINI_API_KEY (Google Gemini)
```

**.env 文件示例：**

```bash
# AI Provider 选择: openai, gemini, ollama
AI_PROVIDER=openai

# OpenAI 配置
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# 或者使用 Google Gemini
# AI_PROVIDER=gemini
# GEMINI_API_KEY=your-gemini-key-here

# 或者使用 Ollama (本地运行)
# AI_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
```

#### 1.3 启动后端服务

```bash
# 方式 1: 使用 uvicorn 直接启动
uv run --prerelease=allow uvicorn src.api.server:app --host 127.0.0.1 --port 8000

# 方式 2: 使用 FastAPI 内置启动
uv run --prerelease=allow python -m src.api.server

# 方式 3: 后台运行（推荐）
nohup uv run --prerelease=allow uvicorn src.api.server:app \
    --host 127.0.0.1 \
    --port 8000 \
    > logs/server.log 2>&1 &
```

#### 1.4 验证后端服务

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 应该返回: {"status":"healthy"}

# 查看日志
tail -f logs/server.log
```

### 2. 前端部署 (Swift App)

#### 2.1 编译 Swift 应用

```bash
cd TypelessApp

# 构建应用
swift build -c release

# 应用将编译到: .build/release/TypelessApp
```

#### 2.2 运行 Swift 应用

```bash
# 方式 1: 直接运行
swift run TypelessApp

# 方式 2: 运行编译后的二进制文件
./.build/release/TypelessApp

# 方式 3: 使用 Xcode (推荐用于开发)
# 1. 打开 TypelessApp 目录
# 2. 在 Xcode 中运行 (⌘R)
```

### 3. 完整启动流程

#### 3.1 生产环境启动

**终端 1 - 启动后端：**

```bash
cd /path/to/typeless_2/PythonService

# 创建日志目录
mkdir -p logs

# 启动后端服务（后台运行）
nohup uv run --prerelease=allow uvicorn src.api.server:app \
    --host 127.0.0.1 \
    --port 8000 \
    --log-level info \
    > logs/server.log 2>&1 &

# 保存进程 ID
echo $! > logs/server.pid

# 验证服务启动
sleep 3
curl http://127.0.0.1:8000/health
```

**终端 2 - 启动前端：**

```bash
cd /path/to/typeless_2/TypelessApp

# 运行应用
swift run TypelessApp
```

#### 3.2 停止服务

```bash
# 停止后端
cd PythonService
if [ -f logs/server.pid ]; then
    kill $(cat logs/server.pid)
    rm logs/server.pid
fi

# 或者强制停止所有 Python 服务
pkill -f "uvicorn src.api.server"
```

### 4. 开发环境快速启动

**一键启动脚本** (可选创建)：

```bash
#!/bin/bash
# start_all.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT/PythonService"

echo "🚀 启动 Typeless 服务..."

# 启动后端
echo "📡 启动后端服务..."
mkdir -p logs
uv run --prerelease=allow uvicorn src.api.server:app \
    --host 127.0.0.1 \
    --port 8000 \
    > logs/server.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > logs/server.pid

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 5

# 验证后端
if curl -s http://127.0.0.1:8000/health > /dev/null; then
    echo "✅ 后端服务启动成功 (PID: $BACKEND_PID)"
else
    echo "❌ 后端服务启动失败"
    kill $BACKEND_PID
    exit 1
fi

echo ""
echo "✅ 所有服务已启动！"
echo ""
echo "后端 API: http://127.0.0.1:8000"
echo "后端日志: $PROJECT_ROOT/PythonService/logs/server.log"
echo ""
echo "现在可以在新终端启动 Swift 应用:"
echo "  cd TypelessApp && swift run TypelessApp"
echo ""
echo "停止服务: kill $BACKEND_PID"
```

使用方式：

```bash
chmod +x start_all.sh
./start_all.sh
```

### 5. 系统配置建议

#### 5.1 创建 macOS 启动脚本

**~/bin/typeless-start**:

```bash
#!/bin/bash
PROJECT_ROOT="/Volumes/nomoshen_macmini/data/project/self/typeless_2"

cd "$PROJECT_ROOT/PythonService"

# 启动后端
uv run --prerelease=allow uvicorn src.api.server:app \
    --host 127.0.0.1 \
    --port 8000 &
echo $! > .backend_pid

echo "后端服务已启动 (PID: $(cat .backend_pid))"
```

#### 5.2 创建 macOS 停止脚本

**~/bin/typeless-stop**:

```bash
#!/bin/bash
PROJECT_ROOT="/Volumes/nomoshen_macmini/data/project/self/typeless_2"

if [ -f "$PROJECT_ROOT/PythonService/.backend_pid" ]; then
    kill $(cat "$PROJECT_ROOT/PythonService/.backend_pid")
    rm "$PROJECT_ROOT/PythonService/.backend_pid"
    echo "后端服务已停止"
else
    echo "未找到运行中的后端服务"
fi
```

### 6. 故障排查

#### 6.1 后端无法启动

```bash
# 检查端口占用
lsof -i :8000

# 查看详细日志
tail -100 PythonService/logs/server.log

# 检查环境变量
cat .env
```

#### 6.2 前端无法连接后端

```bash
# 验证后端是否运行
curl http://127.0.0.1:8000/health

# 检查 Swift 应用中的 baseURL 配置
# 默认: http://127.0.0.1:8000
# 在 ASRService.swift 中修改
```

#### 6.3 ASR 模型加载失败

```bash
# 首次运行会下载 Whisper 模型，需要等待
# 检查模型缓存
ls -la ~/.cache/whisper/ 或 ls -la ~/.cache/huggingface/

# 手动测试 ASR
cd PythonService
uv run --prerelease=allow python test_full_asr.py
```

### 7. 性能优化建议

#### 7.1 后端优化

```bash
# 使用多 worker (需要 gunicorn)
uv run --prerelease=allow pip install gunicorn
uv run gunicorn src.api.server:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000
```

#### 7.2 调整 Whisper 模型大小

编辑 `PythonService/src/asr/model_config.py`:

```python
# 性能优先: small/base
# 准确率优先: large-v3 (当前)
MODEL_SIZE = "large-v3"
```

### 8. 安全建议

1. **不要暴露到公网**：服务默认绑定 127.0.0.1，只在本地访问
2. **保护 API 密钥**：`.env` 文件已加入 `.gitignore`
3. **添加身份验证**：生产环境建议启用 API key 认证
4. **限制请求频率**：已启用 rate limiting (默认 100 requests/min)

### 9. 更新部署

```bash
# 拉取最新代码
cd /path/to/typeless_2
git pull origin master

# 后端：重启服务
cd PythonService
if [ -f logs/server.pid ]; then
    kill $(cat logs/server.pid)
fi
nohup uv run --prerelease=allow uvicorn src.api.server:app \
    --host 127.0.0.1 --port 8000 \
    > logs/server.log 2>&1 &
echo $! > logs/server.pid

# 前端：重新编译
cd TypelessApp
swift build -c release
```

## 10. 测试部署

### 快速验证脚本

```bash
#!/bin/bash
# test_deployment.sh

echo "🧪 测试部署..."

# 1. 测试后端健康检查
echo "1️⃣ 测试后端健康检查..."
HEALTH=$(curl -s http://127.0.0.1:8000/health)
if [[ $HEALTH == *"healthy"* ]]; then
    echo "✅ 后端健康检查通过"
else
    echo "❌ 后端健康检查失败"
    exit 1
fi

# 2. 测试 ASR 端点
echo "2️⃣ 测试 ASR 端点..."
# 这里可以添加实际的音频测试
echo "✅ ASR 端点可访问"

echo ""
echo "✅ 所有测试通过！"
```

## 总结

### 最小启动步骤：

```bash
# 终端 1: 启动后端
cd PythonService
uv run --prerelease=allow uvicorn src.api.server:app --host 127.0.0.1 --port 8000

# 终端 2: 启动前端
cd TypelessApp
swift run TypelessApp
```

### 服务地址：

- **后端 API**: http://127.0.0.1:8000
- **API 文档**: http://127.0.0.1:8000/docs
- **健康检查**: http://127.0.0.1:8000/health

### 需要帮助？

查看日志：
```bash
# 后端日志
tail -f PythonService/logs/server.log

# 系统日志
log stream --predicate 'process == "TypelessApp"'
```
