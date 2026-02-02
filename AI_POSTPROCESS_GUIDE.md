# AI 文本后处理功能使用指南

## 📖 功能介绍

新增的 AI 文本后处理功能支持多种 LLM 提供商，对 Whisper 返回的转录文本进行智能优化：

- ✅ **语法修复** - 修复明显语法错误，移除填充词（嗯、啊、那个）
- ✅ **列表格式化** - 自动识别并格式化列表（有序/无序）
- ✅ **数字转换** - "五" → "5"、"百分之五十" → "50%"
- ✅ **段落组织** - 将长文本分成 2-4 句的短段落
- ✅ **中英文混合** - 保留技术术语（API、GitHub等）
- ✅ **去重** - 移除重复的词语和句子
- ✅ **标点优化** - 使用正确的中文标点符号

## 🚀 快速开始

### 使用 .env 文件配置

所有配置都通过 `PythonService/.env` 文件管理，无需设置环境变量。

```bash
cd PythonService

# 1. 复制示例配置
cp .env.example .env

# 2. 编辑配置
nano .env  # 或使用其他编辑器

# 3. 启动后端（会自动加载 .env）
uv run uvicorn src.api.server:app --host 0.0.0.0 --port 8000
```

### 选项 1：OpenAI（推荐）

编辑 `.env` 文件：

```bash
# 启用 AI 后处理
ENABLE_AI_POSTPROCESS=true
AI_PROVIDER=openai

# OpenAI 配置
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
```

**推荐模型**：
- `gpt-4o-mini` - 性价比高（默认）
- `gpt-4o` - 最强性能

**费用**：
- GPT-4o-mini: $0.15/1M 输入 tokens
- GPT-4o: $2.50/1M 输入 tokens

### 选项 2：OpenAI 中间代理商

如果你使用国内中间代理商，只需设置 `OPENAI_BASE_URL`：

```bash
# .env 文件
ENABLE_AI_POSTPROCESS=true
AI_PROVIDER=openai

# 代理商配置
OPENAI_API_KEY=你的代理商API密钥
OPENAI_BASE_URL=https://api.你的代理商.com/v1
OPENAI_MODEL=gpt-4o-mini
```

**优势**：
- ✅ 无需科学上网
- ✅ 可能有更优惠的价格
- ✅ 不需要修改代码，只需配置 `.env`

### 选项 3：Gemini（免费快速）

编辑 `.env` 文件：

```bash
# 启用 AI 后处理
ENABLE_AI_POSTPROCESS=true
AI_PROVIDER=gemini

# Gemini 配置（从 https://aistudio.google.com/app/apikey 获取）
GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-2.0-flash-exp
```

**推荐模型**：
- `gemini-2.0-flash-exp` - 快速免费（默认）
- `gemini-exp-1206` - 更强性能

**费用**：
- Flash: 每天免费 1500 requests
- Exp: 免费使用

## 🎯 使用方式

### 方式 1：.env 配置 + 实时转录

配置 `.env` 后，录音时自动应用 AI 优化：

```bash
# 编辑 .env
ENABLE_AI_POSTPROCESS=true
AI_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxx

# 重启后端
uv run uvicorn src.api.server:app --host 0.0.0.0 --port 8000

# 正常录音，转录后自动 AI 优化
```

**适用场景**：
- ✅ 录音时自动应用 AI 优化
- ✅ 无需手动调用 API
- ✅ 适合日常使用

### 方式 2：API 调用（手动处理）

对已有文本进行 AI 优化：

```bash
# 使用 OpenAI
curl -X POST "http://localhost:8000/api/asr/ai-enhance" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "嗯 那个 五个 事情 首先 我们需要 做 API 接口",
    "provider": "openai",
    "model": "gpt-4o-mini"
  }'

# 使用 Gemini
curl -X POST "http://localhost:8000/api/asr/ai-enhance" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "嗯 那个 五个 事情 首先 我们需要 做 API 接口",
    "provider": "gemini",
    "model": "gemini-2.0-flash-exp"
  }'
```

**适用场景**：
- ✅ 批量处理已有文本
- ✅ 需要时手动触发
- ✅ 测试不同模型效果

## ⚙️ 配置选项

### .env 文件配置

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `ENABLE_AI_POSTPROCESS` | 否 | false | 是否启用 AI 后处理（实时转录） |
| `AI_PROVIDER` | 否 | openai | LLM 提供商（openai/gemini/ollama） |
| `OPENAI_API_KEY` | OpenAI* | - | OpenAI API 密钥 |
| `OPENAI_BASE_URL` | 否 | - | OpenAI Base URL（用于中间代理商） |
| `OPENAI_MODEL` | 否 | gpt-4o-mini | OpenAI 默认模型 |
| `GEMINI_API_KEY` | Gemini* | - | Google Gemini API 密钥 |
| `GEMINI_MODEL` | 否 | gemini-2.0-flash-exp | Gemini 默认模型 |
| `OLLAMA_BASE_URL` | 否 | http://localhost:11434 | Ollama 服务地址 |
| `OLLAMA_MODEL` | 否 | qwen2.5:7b | Ollama 默认模型 |

*至少需要设置一个提供商的 API Key

### API 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | ✅ | - | 待处理文本 |
| `provider` | string | ❌ | 从 .env | LLM 提供商（openai/gemini/ollama） |
| `model` | string | ❌ | 从 .env | 模型名称（为空使用 .env 中的默认值） |

## 📝 示例

### 示例 1：基本文本优化

**输入**：
```
嗯 那个 五个 事情 首先 我们需要 做 API 接口 设计 然后 实现 它 最后 测试 它
```

**输出**：
```
那 5 件事是：
1. 做 API 接口设计
2. 实现 API 接口设计
3. 测试 API 接口设计
```

### 示例 2：数字转换

**输入**：
```
我买了 三个 iPhone 和 二十 美元的配件
```

**输出**：
```
我买了 3 个 iPhone 和 $20 的配件
```

### 示例 3：中英文混合

**输入**：
```
我们在 GitHub 上找到 Docker 镜像 然后 下载 它
```

**输出**：
```
我们在 GitHub 上找到 Docker 镜像，然后下载它。
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

## 🔧 高级配置

### 使用中间代理商

编辑 `.env` 文件：

```bash
# 中间代理商配置
OPENAI_API_KEY=你的代理商API密钥
OPENAI_BASE_URL=https://api.你的代理商.com/v1
OPENAI_MODEL=gpt-4o-mini
```

**常用代理商**（示例）：
- OpenAI 官方：`https://api.openai.com/v1`（留空即可）
- 国内代理商：按照代理商提供的地址设置

### 自定义 Prompt

编辑 `PythonService/src/postprocess/ai_processor.py`：

```python
POSTPROCESSING_PROMPT = """你的自定义 prompt..."""
```

### 性能优化

**问题**：AI 处理需要额外时间（约 1-3 秒）

**解决方案**：
1. 使用更快的模型：`gpt-4o-mini` 或 `gemini-2.0-flash-exp`
2. 缓存常见结果
3. 异步处理（不阻塞返回）

## 🎯 Power Mode 集成

AI 后处理会根据 Power Mode 自动调整：

| 应用类型 | 行为 |
|---------|------|
| Zed/VSCode | 保留技术术语，格式化代码列表 |
| Word/Notion | 正式语体，清晰段落 |
| 聊天软件 | 非正式语体，去除填充词 |

## 🧪 测试

### 测试 AI 处理

```bash
cd PythonService

# 确保 .env 文件已配置
cat .env

# 运行测试（会自动读取 .env 配置）
uv run python test_ai_postprocess.py
```

### 预期输出

**输入**：`嗯 那个 五个 事情 首先 其次 最后`

**输出**：
```
那 5 件事是：
1. 首先
2. 其次
3. 最后
```

## ⚠️ 注意事项

### .env 文件管理

1. **不要提交到 Git**：`.env` 已在 `.gitignore` 中
2. **模板文件**：使用 `.env.example` 作为配置模板
3. **本地保存**：`.env` 只保存在本地，不分享给他人

### 费用考虑

| 提供商 | 费用模型 | 推荐场景 |
|--------|----------|----------|
| OpenAI 官方 | 按使用量收费 | 需要最高质量 |
| OpenAI 代理商 | 按使用量收费（可能更便宜） | 国内用户 |
| Gemini | 有免费额度 | 日常使用，节省成本 |

### 性能考虑

1. **延迟**：AI 处理增加 1-3 秒延迟
2. **网络**：需要能访问对应 API（或使用代理商）
3. **失败回退**：AI 失败时自动使用规则引擎结果

## 📊 性能对比

| 功能 | 规则引擎 | OpenAI | Gemini |
|------|----------|--------|--------|
| 速度 | ⚡ 快 (<0.1s) | ⚡⚡ (1-2s) | ⚡⚡⚡ (0.5-1s) |
| 准确性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 上下文理解 | ❌ | ✅ | ✅ |
| 成本 | 免费 | 付费 | 免费额度 |
| 网络依赖 | 无 | 需要（或代理商） | 需要 |

## 🎯 推荐使用场景

### 使用规则处理（默认）
- ✅ 快速响应要求高
- ✅ 文本较短（< 50 字）
- ✅ 不需要深度优化

### 使用 AI 处理
- ✅ 重要文档
- ✅ 长文本（> 50 字）
- ✅ 需要高质量输出
- ✅ 有录制好的音频需要转文字

### 提供商选择

| 场景 | 推荐提供商 | 推荐模型 |
|------|-----------|----------|
| 国内用户 | OpenAI 代理商 | gpt-4o-mini |
| 国外用户 | OpenAI 官方 | gpt-4o-mini |
| 免费使用 | Gemini | gemini-2.0-flash-exp |
| 高质量需求 | OpenAI | gpt-4o |
| 离线需求 | Ollama | qwen2.5:7b |

## 📞 故障排查

### 问题 1：AI 处理未生效

**检查**：
```bash
# 查看 .env 配置
cat PythonService/.env | grep ENABLE_AI_POSTPROCESS
```

**解决方案**：
```bash
# 编辑 .env
nano PythonService/.env
# 设置: ENABLE_AI_POSTPROCESS=true

# 重启后端
```

### 问题 2：API 密钥错误

**错误信息**：`OPENAI_API_KEY not found in .env file`

**解决方案**：
```bash
# 编辑 .env
nano PythonService/.env
# 添加: OPENAI_API_KEY=sk-xxx
```

### 问题 3：代理商连接失败

**检查**：
```bash
# 查看 .env 中的 OPENAI_BASE_URL
cat PythonService/.env | grep OPENAI_BASE_URL
```

**解决方案**：
1. 确认代理商地址正确
2. 检查网络连接
3. 联系代理商确认状态

### 问题 4：处理速度慢

**原因**：
1. 模型太大
2. 网络延迟
3. 文本过长

**解决方案**：
- 使用更快的模型：`gpt-4o-mini` 或 `gemini-2.0-flash-exp`
- 检查网络连接或尝试其他代理商
- 缩短文本长度

### 问题 5：如何获取 API Key？

**OpenAI 官方**：
1. 访问：https://platform.openai.com/api-keys
2. 创建 API Key
3. 添加到 .env: `OPENAI_API_KEY=sk-xxx`

**OpenAI 代理商**：
1. 注册代理商账号
2. 获取 API Key
3. 添加到 .env:
   ```
   OPENAI_API_KEY=代理商API密钥
   OPENAI_BASE_URL=代理商API地址
   ```

**Gemini**：
1. 访问：https://aistudio.google.com/app/apikey
2. 创建 API Key
3. 添加到 .env: `GEMINI_API_KEY=xxx`

---

## 📚 相关文档

- [OpenAI 文档](https://platform.openai.com/docs)
- [Gemini 文档](https://ai.google.dev/docs)
- [API 参考](./API.md)
- [快速开始](./AI_QUICKSTART.md)

---

**创建日期**: 2026-02-02
**版本**: 4.0.0 (Env Config + Proxy Support)
**支持**: OpenAI, Gemini, Ollama
**配置方式**: `.env` 文件
