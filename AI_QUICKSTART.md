# 🚀 AI 文本优化功能 - 快速开始

## ✅ 新功能

已添加基于多种 LLM 的文本后处理功能，可以：
- 🧹 清理填充词（嗯、啊、那个）
- 📝 自动格式化列表
- 🔢 数字转换（"五" → "5"）
- 📄 段落组织
- 🌏 中英文混合支持

## ⚙️ 配置方式：使用 .env 文件

### 1. 创建配置文件

```bash
cd PythonService

# 复制示例配置
cp .env.example .env

# 编辑配置文件
nano .env  # 或使用其他编辑器
```

### 2. 配置 OpenAI（推荐）

```bash
# .env 文件内容
ENABLE_AI_POSTPROCESS=true
AI_PROVIDER=openai

# OpenAI 配置
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini

# 如果使用中间代理商，设置自定义 base_url
# OPENAI_BASE_URL=https://api.example.com/v1
```

**推荐模型**：
- `gpt-4o-mini` - 性价比高（默认）
- `gpt-4o` - 最强性能

### 3. 配置 Gemini（免费快速）

```bash
# .env 文件内容
ENABLE_AI_POSTPROCESS=true
AI_PROVIDER=gemini

# Gemini 配置
GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-2.0-flash-exp
```

**推荐模型**：
- `gemini-2.0-flash-exp` - 快速免费（默认）
- `gemini-exp-1206` - 更强性能

### 4. 配置中间代理商（OpenAI）

如果你使用 OpenAI 中间代理商（如国内代理），只需设置 `OPENAI_BASE_URL`：

```bash
# .env 文件内容
ENABLE_AI_POSTPROCESS=true
AI_PROVIDER=openai

OPENAI_API_KEY=你的代理商API密钥
OPENAI_BASE_URL=https://api.你的代理商.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### 5. 启动后端

```bash
cd PythonService
uv run uvicorn src.api.server:app --host 0.0.0.0 --port 8000
```

配置会自动从 `.env` 文件加载！

## 📝 手动调用 API

```bash
# 使用 OpenAI
curl -X POST "http://localhost:8000/api/asr/ai-enhance" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "嗯 那个 五个 事情",
    "provider": "openai",
    "model": "gpt-4o-mini"
  }'

# 使用 Gemini
curl -X POST "http://localhost:8000/api/asr/ai-enhance" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "嗯 那个 五个 事情",
    "provider": "gemini",
    "model": "gemini-2.0-flash-exp"
  }'

# 使用中间代理商（API 调用时指定）
curl -X POST "http://localhost:8000/api/asr/ai-enhance" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "嗯 那个 五个 事情",
    "provider": "openai",
    "model": "gpt-4o-mini"
  }'
# 注意：中间代理商的 base_url 需要在 .env 中配置
```

## 📊 效果对比

### 原始转录（Whisper）
```
嗯 那个 五个 事情 首先 我们需要 做 API 接口 设计 然后 实现 它 最后 测试 它
```

### AI 优化后
```
那 5 件事是：
1. 做 API 接口设计
2. 实现 API 接口设计
3. 测试 API 接口设计
```

## ⚙️ .env 配置选项

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ENABLE_AI_POSTPROCESS` | 启用 AI 后处理 | false |
| `AI_PROVIDER` | 提供商（openai/gemini） | openai |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `OPENAI_BASE_URL` | OpenAI Base URL（用于代理商） | - |
| `OPENAI_MODEL` | OpenAI 默认模型 | gpt-4o-mini |
| `GEMINI_API_KEY` | Gemini API Key | - |
| `GEMINI_MODEL` | Gemini 默认模型 | gemini-2.0-flash-exp |

## 🧪 快速测试

```bash
# 进入 PythonService 目录
cd PythonService

# 确保 .env 文件已配置
cat .env

# 运行测试（会自动检测可用的提供商）
uv run python test_ai_postprocess.py
```

## 🔄 切换提供商

### 方法 1：修改 .env 文件

```bash
# 编辑 .env
nano .env

# 修改提供商
AI_PROVIDER=gemini  # 从 openai 改为 gemini

# 重启后端
uv run uvicorn src.api.server:app --host 0.0.0.0 --port 8000
```

### 方法 2：API 调用时指定

```bash
# 即使 .env 中默认是 OpenAI，也可以临时使用 Gemini
curl -X POST "http://localhost:8000/api/asr/ai-enhance" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "测试文本",
    "provider": "gemini",  # 覆盖 .env 中的设置
    "model": "gemini-2.0-flash-exp"
  }'
```

## ⚠️ 重要提示

1. **不要提交 .env 文件到 Git**：.env 文件已在 .gitignore 中
2. **API 密钥安全**：.env 文件只保存在本地，不分享给他人
3. **中间代理商**：
   - 如果使用国内代理商，设置 `OPENAI_BASE_URL`
   - 不需要修改代码，只需配置 .env
4. **费用**：
   - OpenAI: 按使用量收费
   - Gemini: 有免费额度

## 🔧 获取 API Key

### OpenAI
1. 访问：https://platform.openai.com/api-keys
2. 创建 API Key
3. 复制到 .env: `OPENAI_API_KEY=sk-xxx`

### Gemini
1. 访问：https://aistudio.google.com/app/apikey
2. 创建 API Key
3. 复制到 .env: `GEMINI_API_KEY=xxx`

## 📚 完整文档

详细文档请查看：`AI_POSTPROCESS_GUIDE.md`

---

**状态**：✅ 已集成到后端（使用 .env 配置）
**支持**：OpenAI, Gemini, Ollama
**配置**：编辑 `PythonService/.env` 文件
**测试**：运行 `uv run python test_ai_postprocess.py`
