# 🚀 AI 文本优化功能 - 使用 Ollama

## ✅ 完全免费！无需任何 API 密钥

改用 **Ollama** 本地 LLM，支持多种模型，完全免费！

## 📦 安装步骤

### 1. 安装 Ollama

```bash
# 安装 Ollama（一键安装）
curl -fsSL https://ollama.com/install.sh | sh

# 验证安装
ollama --version
```

### 2. 下载模型

```bash
# 推荐模型（中文优化，7B 参数，速度快）
ollama pull qwen2.5:7b

# 其他可用模型：
# ollama pull llama3:8b           # Llama 3 8B
# ollama pull qwen2:7b-instruct  # 指令版
# ollama pull phi3:mini           # 小型快速模型
```

### 3. 启动 Ollama 服务

```bash
ollama serve
```

Ollama 服务会在后台运行，监听 `http://localhost:11434`

## 🎯 使用方法

### 自动模式（推荐录音时自动应用）

```bash
# 1. 启用 AI 后处理
export ENABLE_AI_POSTPROCESS=true

# 2. 重启后端
uv run uvicorn src.api.server:app --host 0.0.0.0 --port 8000

# 3. 正常录音
# 按下 Right Control 开始/停止，转录后会自动 AI 优化
```

### 手动模式（API 调用）

```bash
curl -X POST "http://localhost:8000/api/asr/ai-enhance" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "嗯 那个 五个 事情 首先 其次 最后",
    "provider": "ollama",
    "model": "qwen2.5:7b"
  }'
```

## 📊 效果示例

### 示例 1：移除填充词 + 格式化

**输入**：
```
嗯 那个 五个 事情 首先 我们需要 做 API 接口 设计 然后 实现 它
```

**输出**：
```
那 5 件事是：
1. 做 API 接口设计
2. 实现 API 接口设计
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

### 示例 3：列表识别

**输入**：
```
要做三件事 编写代码 测试代码 部署代码
```

**输出**：
```
要做 3 件事是：
1. 编写代码
2. 测试代码
3. 部署代码
```

## 🔄 切换模型

### 使用更快的模型

```bash
# 小型快速模型（适合日常使用）
curl -X POST "http://localhost:8000/api/asr/ai-enhance" \
  -H "Content-Type: application/json" \
  -d '{"text": "测试文本", "provider": "ollama", "model": "phi3:mini"}'
```

### 使用更智能的模型

```bash
# 大型模型（更智能但更慢）
curl -X POST "http://localhost:8000/api/asr/ai-enhance" \
  -H "Content-Type: application/json" \
  -d '{"text": "测试文本", "provider": "ollama", "model": "llama3:8b"}'
```

## 📋 推荐模型配置

| 模型 | 参数 | 速度 | 质量 | 推荐场景 |
|------|------|------|------|----------|
| **phi3:mini** | 3.8B | ⚡⚡⚡ | ⭐⭐⭐ | 日常使用 |
| **qwen2.5:7b** | 7B | ⚡⚡ | ⭐⭐⭐⭐ | **推荐** |
| **llama3:8b** | 8B | ⚡ | ⭐⭐⭐⭐⭐ | 高质量需求 |

## 🧪 测试

```bash
# 确保三个服务都在运行
# 1. Ollama 服务
ollama serve &

# 2. 测试 AI 处理
uv run python test_ai_postprocess.py
```

## ⚙️ 配置选项

### 环境变量

| 变量 | 说明 |
|------|------|
| `ENABLE_AI_POSTPROCESS` | 启用 AI 后处理（true/false） |
| `AI_MODEL` | 默认模型（如 qwen2.5:7b） |
| `OLLAMA_BASE_URL` | Ollama 服务地址（默认 http://localhost:11434） |

### 更改默认模型

编辑 `src/postprocess/ai_processor.py` 第 18 行：

```python
model: Optional[str] = "phi3:mini"  # 改成其他模型
```

## 🚀 优势

相比之前的 Claude API 方案：

| 特性 | Claude API | Ollama |
|------|-----------|--------|
| **费用** | 💰 付费（按使用量） | ✅ 完全免费 |
| **API Key** | ❌ 需要 | ✅ 不需要 |
| **网络** | ❌ 需要外网 | ✅ 本地运行 |
| **延迟** | 1-3 秒 | 2-5 秒 |
| **隐私** | ❌ 数据上传 | ✅ 完全本地 |
| **模型选择** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 🎯 总结

✅ **完全免费** - 无需任何 API 密钥
✅ **本地运行** - 数据不外传
✅ **多模型支持** - 随时切换
✅ **统一 API** - OpenAI 兼容格式
✅ **中英优化** - 专门优化的 prompt

---

**创建日期**: 2026-02-02
**状态**: ✅ 已集成
**测试**: 运行 `uv run python test_ai_postprocess.py`
