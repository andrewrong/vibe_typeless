# ✅ Typeless 部署检查清单

## 部署前准备

- [ ] **Python 3.10+ 已安装**
  ```bash
  python --version
  ```

- [ ] **Swift 6.0+ 已安装**
  ```bash
  swift --version
  ```

- [ ] **uv 已安装** (Python 包管理器)
  ```bash
  uv --version || curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- [ ] **至少 8GB 可用内存** (推荐 16GB)

## 后端配置

- [ ] **进入 PythonService 目录**
  ```bash
  cd PythonService
  ```

- [ ] **安装依赖**
  ```bash
  uv sync
  ```

- [ ] **配置 .env 文件**
  ```bash
  cp .env.example .env
  # 编辑 .env，添加 AI API 密钥
  ```

  必须配置以下之一：
  - [ ] `OPENAI_API_KEY` (推荐)
  - [ ] `GEMINI_API_KEY`
  - [ ] `OLLAMA_BASE_URL` (本地运行)

## 后端启动

- [ ] **启动后端服务**
  ```bash
  ./start.sh
  ```

- [ ] **验证服务启动**
  ```bash
  curl http://127.0.0.1:8000/health
  # 应返回: {"status":"healthy"}
  ```

- [ ] **查看日志（如有问题）**
  ```bash
  tail -f logs/server.log
  ```

## 前端启动

- [ ] **打开新终端**

- [ ] **进入 TypelessApp 目录**
  ```bash
  cd TypelessApp
  ```

- [ ] **启动 Swift 应用**
  ```bash
  swift run TypelessApp
  ```

## 验证部署

- [ ] **运行部署测试**
  ```bash
  cd PythonService
  ./test_deployment.sh
  ```

- [ ] **访问 API 文档**
  浏览器打开: http://127.0.0.1:8000/docs

- [ ] **测试转录功能**
  - 在 Swift 应用中录制音频
  - 查看是否返回转录文本

## 故障排查

### 后端无法启动
- [ ] 检查端口占用: `lsof -i :8000`
- [ ] 检查 Python 版本: `python --version`
- [ ] 查看错误日志: `tail -100 logs/server.log`

### 前端无法连接
- [ ] 确认后端已启动: `curl http://127.0.0.1:8000/health`
- [ ] 检查 Swift 应用中的 baseURL 配置

### ASR 不工作
- [ ] 等待模型下载完成（首次运行）
- [ ] 检查 AI API 密钥是否正确配置
- [ ] 查看 ASR 日志: `grep "ASR" logs/server.log`

## 日常使用

### 启动服务
```bash
cd PythonService
./start.sh
```

### 停止服务
```bash
cd PythonService
./stop.sh
```

### 更新代码
```bash
git pull origin master
cd PythonService
./stop.sh
./start.sh
```

## 快速命令参考

| 操作 | 命令 |
|------|------|
| 启动后端 | `cd PythonService && ./start.sh` |
| 停止后端 | `cd PythonService && ./stop.sh` |
| 查看日志 | `tail -f PythonService/logs/server.log` |
| 健康检查 | `curl http://127.0.0.1:8000/health` |
| 测试部署 | `cd PythonService && ./test_deployment.sh` |
| 启动前端 | `cd TypelessApp && swift run TypelessApp` |

## 需要帮助？

- 📖 [详细部署文档](DEPLOYMENT.md)
- 📖 [项目 README](../README.md)
- 🐛 [提交问题](https://github.com/your-repo/issues)

---

**提示**: 首次启动需要下载 Whisper 模型（~3GB），请耐心等待。
