# 部署方式对比

## 部署方式选择

| 特性 | 本地部署 | Docker 部署 |
|------|----------|-------------|
| **安装难度** | 简单 | 中等（需要安装 Docker）|
| **启动速度** | 快 | 中等（需要启动容器）|
| **隔离性** | 共享系统环境 | 完全隔离 |
| **可移植性** | 差（依赖本地环境）| 优秀 |
| **资源占用** | 较低 | 稍高（容器开销）|
| **模型持久化** | ✅ 自动缓存 | ✅ 需要配置 volume |
| **调试方便** | ✅ 非常方便 | ⚠️ 需要进入容器 |
| **版本管理** | 手动管理 | ✅ 固定版本 |
| **多服务管理** | 手动启动 | ✅ docker-compose 一键管理 |

## 推荐场景

### 使用本地部署 (start.sh/stop.sh)

✅ **适合：**
- 开发和调试
- 快速测试新功能
- 经常修改代码
- 熟悉 Python 环境

❌ **不适合：**
- 生产环境
- 需要多实例运行
- 环境需要频繁切换

### 使用 Docker 部署 (docker-start.sh/docker-stop.sh)

✅ **适合：**
- 生产环境部署
- 长期运行服务
- 需要环境隔离
- 多服务协同（如 Ollama）
- 不想污染本地环境

❌ **不适合：**
- 频繁修改代码
- 快速原型开发
- 机器资源有限

## 快速开始对比

### 本地部署

```bash
cd PythonService

# 1. 配置环境
cp .env.example .env
# 编辑 .env

# 2. 启动
./start.sh

# 3. 停止
./stop.sh
```

### Docker 部署

```bash
cd PythonService

# 1. 配置环境
cp .env.example .env
# 编辑 .env

# 2. 启动
./docker-start.sh

# 3. 停止
./docker-stop.sh
```

## 性能对比

### 本地部署

```
启动时间: ~2秒
内存占用: 基准
CPU 占用: 基准
磁盘 I/O: 基准
```

### Docker 部署

```
启动时间: ~5-10秒 (首次构建镜像)
         ~2-3秒 (后续启动)
内存占用: +200-500MB (容器开销)
CPU 占用: 基准
磁盘 I/O: 轻微增加 (层叠文件系统)
```

## 模型管理

### 本地部署

模型自动缓存到：
- `~/.cache/whisper/` - Whisper 模型
- `~/.cache/huggingface/` - HuggingFace 模型

### Docker 部署

模型保存在：
- `./models/` - 可配置的挂载目录

**优点：**
- 可控的存储位置
- 容器删除后模型仍保留
- 方便备份和迁移

## 切换方式

### 从本地切换到 Docker

```bash
# 1. 停止本地服务
cd PythonService
./stop.sh

# 2. 启动 Docker 服务
./docker-start.sh

# 3. (可选) 复制本地模型到 Docker 挂载点
cp -r ~/.cache/whisper/* ./models/whisper/
```

### 从 Docker 切换到本地

```bash
# 1. 停止 Docker 服务
cd PythonService
./docker-stop.sh

# 2. 启动本地服务
./start.sh
```

## 混合使用

可以在开发时使用本地部署，生产环境使用 Docker：

```bash
# 开发环境
cd PythonService
./start.sh  # 本地部署，方便调试

# 生产环境
./docker-start.sh  # Docker 部署，稳定隔离
```

## 故障排查对比

### 本地部署问题

```bash
# 查看进程
ps aux | grep uvicorn

# 查看端口
lsof -i :8000

# 查看日志
tail -f logs/server.log
```

### Docker 部署问题

```bash
# 查看容器
docker-compose ps

# 查看日志
docker-compose logs -f

# 进入容器
docker-compose exec typeless-backend bash

# 查看资源
docker stats typeless-backend
```

## 最佳实践

### 开发环境

**推荐：本地部署**

```bash
# 使用本地 Python，方便调试
./start.sh

# 修改代码后重启
./stop.sh && ./start.sh
```

### 生产环境

**推荐：Docker 部署**

```bash
# 使用 Docker，稳定隔离
./docker-start.sh

# 后台运行，自动重启
restart: unless-stopped  # docker-compose.yml
```

### 测试环境

**推荐：Docker Compose**

```bash
# 完整的测试环境（包含 Ollama）
docker-compose up -d
```

## 总结

| 阶段 | 推荐方式 |
|------|----------|
| **开发调试** | 本地部署 |
| **功能测试** | 本地部署 |
| **性能测试** | Docker 部署 |
| **生产运行** | Docker 部署 |
| **CI/CD** | Docker 部署 |

选择适合你的方式即可！两者都支持完整的功能。
