# Typeless macOS 平替项目规范

## 项目概述

在 macOS 平台上实现 Typeless 的平替服务，使用 MLX 本地运行 ASR 模型作为推理服务，支持本地和云端 LLM 后处理。

## 技术栈

- **Swift**: SwiftUI + Swift Testing (系统集成、UI、音频捕获、文本注入)
- **Python**: uv + pytest + MLX (ASR 推理服务、LLM 后处理)
- **通信**: HTTP/WebSocket

## 项目架构

```
┌─────────────────────────────────────────────────────────────┐
│  Swift (SwiftUI + Swift Testing)                            │
│  - 系统集成、UI、音频捕获、文本注入                           │
└─────────────────────────────────────────────────────────────┘
                          │
                    HTTP/WebSocket
                          │
┌─────────────────────────────────────────────────────────────┐
│  Python (uv + pytest)                                       │
│  - MLX ASR 推理服务                                         │
│  - 本地 LLM 后处理 (可选)                                   │
│  - 云端 LLM 集成                                            │
└─────────────────────────────────────────────────────────────┘
```

## TDD 开发流程规范

### 工作流程

```
1. 编写失败测试 (Red)
   ↓
2. 编写最小实现 (Green)
   ↓
3. 重构优化 (Refactor)
   ↓
4. 运行所有测试 (确保无回归)
```

### 测试要求

- **Swift**: Swift Testing 框架
- **Python**: pytest + pytest-asyncio
- **覆盖率**: 目标 > 80%
- **CI/CD**: GitHub Actions 自动运行测试

### 测试先行原则

所有功能模块必须先编写测试用例，再实现功能代码：
1. 编写失败测试
2. 实现最小功能使测试通过
3. 重构优化代码
4. 运行全部测试确保无回归

## Git 提交规范

### 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

- `feat`: 新功能
- `fix`: 修复 bug
- `test`: 添加测试
- `docs`: 文档更新
- `refactor`: 代码重构
- `style`: 代码格式调整
- `perf`: 性能优化
- `chore`: 构建/工具变更

### Scope 范围

- `asr`: ASR 服务
- `postprocess`: 后处理服务
- `audio`: 音频捕获
- `text`: 文本注入
- `ui`: 用户界面
- `app`: 应用整体

### 示例

```
feat(audio): add audio recorder module
fix(asr): fix streaming endpoint connection leak
test(postprocess): add tests for filler removal
docs: update CLAUDE.md with architecture diagram
refactor(services): extract cloud provider interface
```

## 依赖管理规范

### Python (uv)

```bash
# 初始化项目
uv init

# 添加依赖
uv add <package-name>

# 添加开发依赖
uv add --dev <package-name>

# 锁定依赖
uv lock

# 运行应用
uv run python src/asr/server.py

# 运行测试
uv run pytest

# 运行测试并生成覆盖率报告
uv run pytest --cov=src --cov-report=html
```

### Swift (SPM)

```bash
# 构建项目
swift build

# 运行应用
swift run

# 运行测试
swift test

# 添加依赖 (编辑 Package.swift)
# 然后执行:
swift package resolve
```

## 项目结构

```
typeless_2/
├── CLAUDE.md                 # 项目规范文档 (Git 管理)
├── README.md                 # 项目说明
├── .git/                     # Git 版本控制
├── .gitignore
│
├── SwiftApp/                 # SwiftUI 应用
│   ├── App/
│   │   ├── TypelessApp.swift           # 应用入口
│   │   ├── ContentView.swift           # 主界面
│   │   └── TypelessAppTests.swift      # Swift Testing
│   ├── Core/
│   │   ├── AudioRecorder/              # 音频捕获模块
│   │   ├── TextInjector/               # 文本注入模块
│   │   ├── AppDetector/                # 前台应用检测
│   │   └── HotkeyManager/              # 全局快捷键
│   ├── Services/
│   │   ├── ASRService.swift            # ASR 客户端
│   │   └── PostProcessor.swift         # 后处理客户端
│   ├── Resources/                      # 资源文件
│   └── Package.swift                   # SPM 配置
│
├── PythonService/            # Python 推理服务
│   ├── pyproject.toml        # uv 项目配置
│   ├── uv.lock               # uv 锁文件
│   ├── src/
│   │   ├── asr/
│   │   │   ├── __init__.py
│   │   │   ├── model.py              # MLX ASR 模型
│   │   │   ├── server.py             # HTTP 服务
│   │   │   └── stream.py             # 流式处理
│   │   ├── postprocess/
│   │   │   ├── __init__.py
│   │   │   ├── local_llm.py          # MLX LLM 后处理
│   │   │   ├── cloud_llm.py          # 云端 LLM 集成
│   │   │   └── processor.py          # 规则引擎
│   │   └── api/
│   │       ├── __init__.py
│   │       └── routes.py             # FastAPI 路由
│   ├── tests/
│   │   ├── test_asr.py               # ASR 测试 (pytest)
│   │   ├── test_postprocess.py       # 后处理测试
│   │   └── fixtures/                 # 测试数据
│   └── README.md
│
└── docs/                     # 文档
    ├── ARCHITECTURE.md        # 架构设计
    └── API.md                 # API 文档
```

## 测试覆盖率要求

- **单元测试覆盖率**: 目标 > 80%
- **关键路径覆盖率**: 100%
- **集成测试**: 覆盖主要用户场景

## 代码规范

### Python

- 遵循 PEP 8 规范
- 使用 ruff 进行代码检查
- 使用 mypy 进行类型检查

### Swift

- 遵循 Swift API 设计指南
- 使用 SwiftLint 进行代码检查
- 代码格式化使用 SwiftFormat

## 性能要求

- **ASR 延迟**: < 500ms
- **后处理延迟**: < 1s
- **内存占用**: < 4GB (包含模型)
- **CPU 占用**: < 50% (M系列芯片)

## 安全规范

- API 密钥通过环境变量管理
- 不在代码中硬编码敏感信息
- 使用 .gitignore 排除敏感文件

## 开发工作流

1. 从 main 分支创建 feature 分支
2. 按照 TDD 流程开发
3. 运行测试确保通过
4. 提交代码并推送到远程
5. 创建 Pull Request
6. 通过 CI/CD 检查
7. Code Review
8. 合并到 main 分支

## 文档要求

- 所有公开 API 必须有文档注释
- 关键算法需要详细注释
- 重大变更更新相关文档

## 版本发布

- 遵循语义化版本规范 (Semantic Versioning)
- 维护 CHANGELOG.md
- 标记重要版本
