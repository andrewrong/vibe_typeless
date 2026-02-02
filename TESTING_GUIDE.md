# Typeless 新功能测试指南

## 🎯 功能概览

### 1. Personal Dictionary（个人词典）
自动将你说的词替换成正确的写法。

**例子：**
- 说 "api" → 输出 "API"
- 说 "docker" → 输出 "Docker"
- 说 "阿里云" → 输出 "阿里云"

### 2. Power Mode（智能应用检测）
根据当前使用的应用自动调整转录策略。

**例子：**
- 在 **Xcode** 中 → 不加标点，保留大小写（适合代码）
- 在 **微信** 中 → 口语化，加标点
- 在 **Notion** 中 → 完整标点，格式化

---

## 📝 测试步骤

### 测试 1：验证 Personal Dictionary

#### 步骤 1：查看默认词典
```bash
curl -s http://127.0.0.1:8000/api/asr/dictionary | python3 -m json.tool
```

你会看到 19 个默认条目，包括：
- Tech terms: API, Docker, Kubernetes, Git, GitHub, Python, JavaScript 等
- Companies: 阿里云, 腾讯, 字节跳动, 百度, 华为

#### 步骤 2：添加自定义词条
```bash
curl -X POST http://127.0.0.1:8000/api/asr/dictionary \
  -H "Content-Type: application/json" \
  -d '{
    "spoken": "llm",
    "written": "LLM",
    "category": "ai"
  }'
```

#### 步骤 3：实际测试
1. 按 **Right Control** 开始录音
2. 说："测试 api 和 llm 模型"
3. 再按 **Right Control** 停止
4. **预期输出**："测试 API 和 LLM 模型"（自动大写）

---

### 测试 2：验证 Power Mode

#### 步骤 1：在 Coding 应用中测试
1. 打开 **Xcode** 或 **VSCode**
2. 按 **Right Control** 录音
3. 说："定义一个函数叫 calculate sum 参数是两个整数"
4. 停止录音
5. **预期**：不加标点，保留技术术语大小写

**查看日志确认：**
```bash
tail -20 /tmp/backend_pm.log | grep "Power Mode"
```

你应该看到：
```
📱 Power Mode: Xcode|com.apple.dt.Xcode → coding
   Config: punctuation=False, technical=True
```

#### 步骤 2：在 Writing 应用中测试
1. 打开 **TextEdit** 或 **Notion**
2. 按 **Right Control** 录音
3. 说："今天天气很好，我想出去玩"
4. 停止录音
5. **预期**：添加标点符号

**查看日志：**
```bash
tail -20 /tmp/backend_pm.log | grep "Power Mode"
```

你应该看到：
```
📱 Power Mode: TextEdit|com.apple.TextEdit → writing
   Config: punctuation=True, technical=False
```

#### 步骤 3：在 Chat 应用中测试
1. 打开 **微信** 或其他聊天应用
2. 按 **Right Control** 录音
3. 说一些口语化的内容
4. 停止录音
5. **预期**：保留口语风格，加标点

---

### 测试 3：组合效果

**场景：在 Xcode 中写代码注释**
1. 打开 **Xcode**
2. 按 **Right Control** 录音
3. 说："这个函数使用 docker 容器运行 api 服务"
4. 停止录音

**预期输出：**
```
这个函数使用 Docker 容器运行 API 服务
```
- ✅ **Docker** 和 **API** 自动大写（Dictionary）
- ✅ 不加标点（Power Mode for coding）
- ✅ 保留技术术语（Power Mode）

---

## 🔍 调试技巧

### 查看后端日志
```bash
# 实时查看日志
tail -f /tmp/backend_pm.log

# 查看 Power Mode 检测
grep "Power Mode" /tmp/backend_pm.log

# 查看 Dictionary 替换
grep "dictionary replacements" /tmp/backend_pm.log
```

### 查看完整转录流程
```bash
grep -E "(Power Mode|VAD|Transcribing|Final)" /tmp/backend_pm.log | tail -30
```

**示例输出：**
```
📱 Power Mode: Xcode|com.apple.dt.Xcode → coding
   Config: punctuation=False, technical=True
🎛️ Applying audio processing pipeline...
   VAD: 1 speech segments, removed 2.3s silence
   Transcribing segment 1/1 (120000 samples)
Applied 2 dictionary replacements
✅ Final transcript: '使用 Docker 容器部署 API 服务'
```

---

## 🛠️ 管理你的词典

### 查看所有词条
```bash
curl -s http://127.0.0.1:8000/api/asr/dictionary | python3 -m json.tool > /tmp/dict.json
cat /tmp/dict.json
```

### 添加新词条
```bash
curl -X POST http://127.0.0.1:8000/api/asr/dictionary \
  -H "Content-Type: application/json" \
  -d '{
    "spoken": "你的词",
    "written": "正确写法",
    "category": "custom",
    "case_sensitive": false,
    "whole_word": false
  }'
```

### 删除词条
```bash
curl -X DELETE http://127.0.0.1:8000/api/asr/dictionary/你的词
```

### 清空所有自定义词条（保留默认）
```bash
curl -X POST http://127.0.0.1:8000/api/asr/dictionary/clear
```

---

## 📊 支持的应用

### Coding（代码）
- Xcode
- VSCode
- JetBrains IDEs
- Sublime Text

### Writing（写作）
- Notion
- Word
- Pages
- TextEdit

### Chat（聊天）
- WeChat (微信)
- Slack
- Discord

### Browser（浏览器）
- Chrome
- Safari
- Firefox

### Terminal（终端）
- Terminal
- iTerm2

---

## 💡 使用建议

### 适合开发者的配置
```bash
# 添加你的常用技术术语
curl -X POST http://127.0.0.1:8000/api/asr/dictionary \
  -H "Content-Type: application/json" \
  -d '{"spoken": "numpy", "written": "NumPy", "category": "tech"}'

curl -X POST http://127.0.0.1:8000/api/asr/dictionary \
  -H "Content-Type: application/json" \
  -d '{"spoken": "pandas", "written": "Pandas", "category": "tech"}'
```

### 适合写作者的配置
```bash
# 添加常用的中文词汇
curl -X POST http://127.0.0.1:8000/api/asr/dictionary \
  -H "Content-Type: application/json" \
  -d '{"spoken": "人工智能", "written": "人工智能", "category": "writing"}'
```

---

## 🐛 常见问题

### Q: Dictionary 没有生效？
**A:** 检查日志：
```bash
grep "dictionary replacements" /tmp/backend_pm.log
```
如果没有看到 "Applied X dictionary replacements"，说明：
1. 没有匹配到词汇
2. 大小写不匹配

### Q: Power Mode 检测错误？
**A:** 查看日志确认应用检测：
```bash
grep "Power Mode" /tmp/backend_pm.log
```

### Q: 如何禁用某个功能？
**A:**
- Dictionary: 删除词条或清空
- Power Mode: 目前无法禁用，但可以添加到 "general" 类别

---

## ✅ 快速验证清单

运行这个脚本验证所有功能：

```bash
# 检查后端状态
curl -s http://127.0.0.1:8000/health

# 查看 Dictionary
echo "📚 Dictionary has $(curl -s http://127.0.0.1:8000/api/asr/dictionary | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])") entries"

# 添加测试词条
curl -s -X POST http://127.0.0.1:8000/api/asr/dictionary \
  -H "Content-Type: application/json" \
  -d '{"spoken": "testword", "written": "TestWord", "category": "test"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])"

# 验证添加成功
curl -s http://127.0.0.1:8000/api/asr/dictionary | python3 -c "
import sys, json
data = json.load(sys.stdin)
if any(e['spoken'] == 'testword' for cat in data['entries'].values() for e in cat):
    print('✅ Test entry added successfully')
else:
    print('❌ Test entry not found')
"

# 清理测试词条
curl -X DELETE http://127.0.0.1:8000/api/asr/dictionary/testword > /dev/null 2>&1
echo "🧹 Cleanup complete"
```

---

准备好测试了吗？从 **测试 1** 开始！
