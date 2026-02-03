# Typeless Docker 部署指南

## 为什么使用 Docker？

✅ **环境隔离** - 不污染本地 Python 环境
✅ **一键部署** - 自动处理所有依赖
✅ **版本管理** - 固定运行环境版本
✅ **模型持久化** - 模型文件只下载一次
✅ **便于扩展** - 支持多服务编排

## 系统要求

- Docker Desktop 4.0+ (macOS)
- 至少 8GB 内存（推荐 16GB）
- 20GB 可用磁盘空间（包含模型）

## 快速开始

### 1. 启动服务

```bash
cd PythonService

# 一键启动
./docker-start.sh
```

### 2. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 访问 API 文档
# 浏览器打开: http://localhost:8000/docs
```

### 3. 停止服务

```bash
./docker-stop.sh
```

## 详细说明

### 目录结构

```
PythonService/
├── Dockerfile              # Docker 镜像定义
├── docker-compose.yml      # 服务编排配置
├── .dockerignore          # Docker 忽略文件
├── docker-start.sh        # 启动脚本
├── docker-stop.sh         # 停止脚本
├── models/                # 模型缓存目录 (自动创建)
│   ├── whisper/           # Whisper 模型
│   └── huggingface/       # HuggingFace 缓存
└── logs/                  # 日志目录
```

### 模型持久化

默认情况下，模型文件会保存在 `./models` 目录：

```yaml
volumes:
  - ./models:/app/models
```

**优点：**
- 首次下载后，模型永久保存
- 重启容器无需重新下载
- 可以手动备份模型文件

**修改缓存路径：**

```bash
# 方式 1: 环境变量
export MODEL_CACHE_PATH=/path/to/models
./docker-start.sh

# 方式 2: 修改 docker-compose.yml
volumes:
  - /your/custom/path:/app/models
```

### 环境变量配置

在 `docker-compose.yml` 中配置：

```yaml
environment:
  # AI Provider (必选其一)
  - AI_PROVIDER=openai           # 或 gemini, ollama
  - OPENAI_API_KEY=sk-your-key   # OpenAI
  - GEMINI_API_KEY=your-key      # Gemini
  - OLLAMA_BASE_URL=http://...   # Ollama

  # 性能调优
  - RATE_LIMIT_ENABLED=true
  - LOG_LEVEL=INFO
```

**或使用 `.env` 文件：**

```bash
# .env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
MODEL_CACHE_PATH=./models
```

## 常用命令

### 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看实时日志
docker-compose logs -f typeless-backend
```

### 容器管理

```bash
# 进入容器
docker-compose exec typeless-backend bash

# 在容器中执行命令
docker-compose exec typeless-backend uv run python --version

# 查看容器资源使用
docker stats typeless-backend
```

### 镜像管理

```bash
# 重新构建镜像
docker-compose build --no-cache

# 查看镜像
docker images | grep typeless

# 清理未使用的镜像
docker image prune
```

## 高级配置

### 资源限制

编辑 `docker-compose.yml`：

```yaml
deploy:
  resources:
    limits:
      cpus: '4'      # 最大 CPU 核心数
      memory: 8G    # 最大内存
    reservations:
      cpus: '2'     # 保留 CPU 核心数
      memory: 4G    # 保留内存
```

**根据你的机器调整：**

| 配置 | 轻量级 | 标准配置 | 高性能 |
|------|---------|----------|--------|
| CPU | 2 核 | 4 核 | 8 核 |
| 内存 | 4GB | 8GB | 16GB |

### 多服务部署

如果需要同时运行 Ollama：

```yaml
services:
  typeless-backend:
    # ... (后端配置)

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

### 自定义网络

```yaml
networks:
  typeless-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## 故障排查

### 1. 端口被占用

```bash
# 检查端口 8000
lsof -i :8000

# 修改 docker-compose.yml 中的端口映射
ports:
  - "8080:8000"  # 改用 8080
```

### 2. 容器启动失败

```bash
# 查看详细日志
docker-compose logs --tail=100

# 检查容器状态
docker-compose ps -a

# 重新构建
docker-compose build --no-cache
docker-compose up -d
```

### 3. 模型下载失败

```bash
# 进入容器
docker-compose exec typeless-backend bash

# 手动测试下载
uv run python -c "from whisper import load_model; m = load_model('large-v3')"

# 检查模型目录
ls -la /app/models/
```

### 4. 内存不足

```bash
# 查看资源使用
docker stats

# 增加内存限制
# 编辑 docker-compose.yml，增加 memory 限制

# 或使用更小的模型
# 编辑 src/asr/model_config.py
MODEL_SIZE = "base"  # 改用 base 模型
```

### 5. 网络连接问题

```bash
# 从容器内测试外网
docker-compose exec typeless-backend curl https://api.openai.com

# 检查 DNS
docker-compose exec typeless-backend cat /etc/resolv.conf
```

## 性能优化

### 1. 使用多阶段构建

```dockerfile
# 构建阶段
FROM python:3.11-slim as builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# 运行阶段
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
...
```

### 2. 镜像缓存

```bash
# 构建时使用缓存
docker-compose build

# 强制重新构建
docker-compose build --no-cache
```

### 3. 日志管理

```yaml
# docker-compose.yml
services:
  typeless-backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 更新部署

### 更新代码

```bash
# 1. 拉取最新代码
git pull origin master

# 2. 重新构建并启动
docker-compose down
docker-compose build
docker-compose up -d
```

### 滚动更新（零停机）

```bash
# 启动新容器
docker-compose up -d --no-deps --build typeless-backend

# 等待新容器就绪后，停止旧容器
# Docker Compose 会自动处理
```

## 备份与恢复

### 备份模型文件

```bash
# 打包模型目录
tar -czf models-backup-$(date +%Y%m%d).tar.gz models/

# 恢复
tar -xzf models-backup-20250203.tar.gz
```

### 备份配置

```bash
# 备份 .env 和其他配置
tar -czf config-backup.tar.gz .env docker-compose.yml
```

## 生产环境建议

### 1. 使用非 root 用户

```dockerfile
RUN useradd -m -u 1000 typeless
USER typeless
WORKDIR /app
```

### 2. 安全加固

```yaml
# docker-compose.yml
security_opt:
  - no-new-privileges:true
read_only: true
tmpfs:
  - /tmp
```

### 3. 监控

```bash
# 添加健康检查监控
watch -n 5 'curl -s http://localhost:8000/health | jq .'
```

### 4. 日志收集

```bash
# 使用 ELK 或其他日志系统
# docker-compose.yml
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://logserver:514"
```

## 与本地开发切换

### Docker → 本地

```bash
# 停止 Docker 服务
./docker-stop.sh

# 启动本地服务
./start.sh
```

### 本地 → Docker

```bash
# 停止本地服务
./stop.sh

# 启动 Docker 服务
./docker-start.sh
```

## 常见问题

**Q: Docker 镜像太大？**
A: 正常，因为包含 Python 环境和依赖。可以使用 `docker-slim` 优化。

**Q: 模型下载慢？**
A: 可以手动下载模型文件放到 `./models` 目录，然后重启容器。

**Q: 如何在容器内调试？**
A: 使用 `docker-compose exec typeless-backend bash` 进入容器。

**Q: 能在 Apple Silicon 以外的机器运行吗？**
A: 可以，但 MLX 优化的 Whisper 只在 Apple Silicon 上最快。其他平台会使用 CPU 模式。

**Q: 如何查看实时日志？**
A: `docker-compose logs -f` 或 `tail -f logs/server.log`

## 参考资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [MLX 文档](https://ml-explore.github.io/mlx/)

---

**提示**: 首次启动会下载 Docker 镜像和模型，请耐心等待。
