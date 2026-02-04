# 🚀 Typeless 本地部署快速指南

## ⚡ 5 分钟快速部署

### 步骤 1：检查环境

```bash
cd PythonService

# 检查 Python 版本（需要 3.10+）
python --version
```

**如果 Python 版本不对：**
```bash
# macOS 使用 Homebrew 安装 Python 3.11
brew install python@3.11
```

### 步骤 1.5：迁移现有文件（可选）

如果你之前运行过 Typeless，可以迁移旧的模型和日志：

```bash
# 运行迁移脚本
./migrate_runtime.sh
```

这会将：
- 旧的日志从 `logs/` 移动到 `runtime/logs/`
- 模型从 `~/.cache/huggingface/` 移动到 `runtime/models/`

### 步骤 2：安装依赖

```bash
# 安装 uv（Python 包管理器）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv sync
```

### 步骤 3：配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件
nano .env  # 或使用其他编辑器
```

**必须配置以下之一：**

```bash
# 方式 1: OpenAI（推荐）
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here

# 方式 2: Google Gemini
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key-here

# 方式 3: Ollama（本地免费）
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

### 步骤 4：启动后端服务

```bash
# 一键启动
./start.sh
```

**启动成功会显示：**
```
✅ 后端服务已启动！

📍 服务地址:
   - API: http://127.0.0.1:28111
   - 文档: http://127.0.0.1:28111/docs
   - 健康检查: http://127.0.0.1:28111/health
```

### 步骤 5：验证服务

```bash
# 健康检查
curl http://127.0.0.1:28111/health

# 应该返回: {"status":"healthy"}

# 或运行验证脚本
./test_deployment.sh
```

### 步骤 6：启动前端应用

**新开一个终端：**

```bash
cd TypelessApp

# 启动 Swift 应用
swift run TypelessApp
```

## 📋 完整命令流程

```bash
# 终端 1：启动后端
cd PythonService
cp .env.example .env
nano .env  # 配置 API 密钥
./start.sh

# 终端 2：启动前端
cd TypelessApp
swift run TypelessApp
```

## ✅ 验证部署

### 测试后端 API

```bash
# 1. 健康检查
curl http://127.0.0.1:28111/health

# 2. 查看 API 文档
# 浏览器打开: http://127.0.0.1:28111/docs

# 3. 测试转录
cd PythonService
curl -X POST \
  -H "Content-Type: application/octet-stream" \
  --data-binary @test_audio.wav \
  http://127.0.0.1:28111/api/asr/transcribe
```

### 查看日志

```bash
# 实时查看日志
tail -f runtime/logs/server.log

# 查看最近 50 行
tail -50 runtime/logs/server.log
```

## 🛑 停止服务

### 停止后端

```bash
cd PythonService
./stop.sh
```

### 停止前端

在 Swift 应用终端按 `Cmd + Q` 或 `Ctrl + C`

## 📂 运行时目录结构

所有运行时文件都存放在 `runtime/` 目录下：

```
runtime/
├── logs/              # 应用日志
│   ├── server.log         # 服务器日志
│   └── server.pid         # 进程 ID
├── models/            # 模型缓存（自动下载）
│   └── hub/               # HuggingFace 模型
└── tmp/              # 临时文件
```

### 查看模型和日志大小

```bash
# 查看 runtime 目录大小
du -sh runtime/

# 查看各个模型的大小
du -sh runtime/models/hub/models--mlx-community--whisper-*
```

### 清理模型

如果需要释放空间：

```bash
# 删除不需要的模型
rm -rf runtime/models/hub/models--mlx-community--whisper-medium-mlx
```

更多详情请查看 [runtime/README.md](runtime/README.md)

## 🔄 日常使用

### 启动服务

```bash
cd PythonService
./start.sh
```

### 重启服务

```bash
cd PythonService
./stop.sh
./start.sh
```

### 更新代码后重启

```bash
cd PythonService

# 拉取最新代码
git pull

# 重启服务
./stop.sh
./start.sh
```

## 🔧 故障排查

### 问题 1：端口被占用

```bash
# 检查端口 28111
lsof -i :28111

# 如果被占用，查找进程
ps aux | grep uvicorn

# 停止旧进程
kill <PID>
```

### 问题 2：Python 版本不对

```bash
# 检查版本
python --version

# 使用正确的 Python
python3 --version

# 或使用 uv 运行
uv run python --version
```

### 问题 3：依赖安装失败

```bash
# 清理缓存重新安装
rm -rf .venv
uv sync
```

### 问题 4：模型下载慢

```bash
# 首次运行会下载 Whisper 模型（~3GB）
# 请耐心等待，或手动下载模型到缓存目录

# 模型缓存位置：
# ~/.cache/whisper/
# ~/.cache/huggingface/
```

### 问题 5：API 密钥无效

```bash
# 检查 .env 文件
cat .env

# 确保 API 密钥正确配置
# OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=...
```

## 📊 性能优化

### 使用更小的模型（如果内存不足）

编辑 `src/asr/model_config.py`：

```python
# 可选: "tiny", "base", "small", "medium", "large-v3"
MODEL_SIZE = "base"  # 从 "large-v3" 改为 "base"
```

**性能对比：**
- `large-v3`: 准确率最高，速度最慢，内存 4-6GB
- `base`: 平衡，速度快，内存 2-3GB
- `small`: 最快，准确率略低，内存 1-2GB

### 调整并发数

编辑 `src/api/server.py`：

```python
# uvicorn 配置
uvicorn.run(app, host="127.0.0.1", port=28111, workers=1)
#                                           ^^^^^^
# 增加 workers 可以处理更多并发请求（需要更多内存）
```

## 🚀 开机自启动（可选）

### 使用 launchd（macOS 推荐）

**创建 ~/Library/LaunchAgents/com.typeless.backend.plist**：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PLIST-1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.typeless.backend</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/zsh</string>
        <string>-c</string>
        <string>cd /path/to/PythonService && ./start.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/path/to/PythonService</string>
    <key>StandardOutPath</key>
    <string>/path/to/PythonService/logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/PythonService/logs/launchd.err</string>
</dict>
</plist>
```

**加载服务：**

```bash
# 加载
launchctl load ~/Library/LaunchAgents/com.typeless.backend.plist

# 启动
launchctl start com.typeless.backend

# 停止
launchctl unload ~/Library/LaunchAgents/com.typeless.backend.plist
```

## 📱 创建桌面快捷方式

### 创建启动脚本

**~/bin/typeless**:

```bash
#!/bin/bash
cd /path/to/PythonService
./start.sh
```

**创建停止脚本**

**~/bin/typeless-stop**:

```bash
#!/bin/bash
cd /path/to/PythonService
./stop.sh
```

### 使用 macOS Automator

1. 打开 Automator
2. 创建新应用
3. 添加"运行 Shell 脚本"操作
4. 输入命令：`cd /path/to/PythonService && ./start.sh`
5. 保存为 "Typeless Backend.app"

## 📚 相关文档

- [完整部署指南](DEPLOYMENT.md) - 详细部署说明
- [部署检查清单](CHECKLIST.md) - 部署验证清单
- [API 文档](http://127.0.0.1:28111/docs) - 交互式 API 文档

## ✅ 部署检查清单

- [ ] Python 3.10+ 已安装
- [ ] uv 已安装
- [ ] 依赖已安装（`uv sync`）
- [ ] .env 文件已配置
- [ ] API 密钥已设置
- [ ] 后端服务启动成功
- [ ] 健康检查通过
- [ ] Swift 应用可启动

## 🎉 完成！

现在你可以：

1. **使用语音转文字功能**
   - 启动 Swift 应用
   - 录制语音
   - 实时看到转录结果

2. **查看 API 文档**
   - 访问 http://127.0.0.1:28111/docs
   - 试用 API 端点

3. **监控服务状态**
   - 查看日志：`tail -f logs/server.log`
   - 健康检查：`curl http://127.0.0.1:28111/health`

---

**需要帮助？** 查看 [DEPLOYMENT.md](DEPLOYMENT.md) 或 [CHECKLIST.md](CHECKLIST.md)
