"""
AI 文本后处理测试脚本
支持 OpenAI, Gemini, Ollama
配置通过 .env 文件管理
"""
import sys
import asyncio

sys.path.insert(0, '.')

from src.postprocess.ai_processor import AIPostProcessor, PostProcessRequest
from src.config import settings

# 测试用例
test_cases = [
    {
        "name": "基本优化 - 移除填充词",
        "input": "嗯 那个 五个 事情 首先 我们需要 做 API 接口 设计 然后 实现 它 最后 测试 它",
        "expected_keywords": ["5件事", "API", "1.", "2.", "3.", "4.", "5."],
    },
    {
        "name": "数字转换",
        "input": "我买了 三个 iPhone 和 二十 美元的配件",
        "expected_keywords": ["3", "iPhone", "$20"],
    },
    {
        "name": "列表格式化",
        "input": "要做三件事 第一 编写代码 第二 测试 第三 部署",
        "expected_keywords": ["3件事", "1.", "2.", "3."],
    },
    {
        "name": "中英文混合",
        "input": "我们在 GitHub 上找到 Docker 镜像 然后 下载 它",
        "expected_keywords": ["GitHub", "Docker", "下载"],
    },
    {
        "name": "段落组织",
        "input": "这是一个很长的文本包含很多内容需要分成多个段落来提高可读性应该有更好的结构",
        "expected_keywords": ["段落"],
    },
    {
        "name": "去重复",
        "input": "你好 你好 我想 我想 说 去商店",
        "expected_keywords": ["你好", "想", "说", "去商店"],
    },
]


async def test_provider(processor: AIPostProcessor, provider: str, model: str):
    """测试指定提供商"""
    print(f"\n{'=' * 60}")
    print(f"测试提供商: {provider} ({model})")
    print('=' * 60)

    # 运行测试
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"测试 {i}/{len(test_cases)}: {test['name']}")
        print('=' * 60)

        print(f"\n输入 ({len(test['input'])} 字符):")
        print(f"  {test['input']}")

        try:
            request = PostProcessRequest(
                text=test['input'],
                provider=provider,
                model=model
            )

            response = await processor.process(request)

            print(f"\n输出 ({len(response.processed)} 字符):")
            print(f"  {response.processed}")

            # 检查期望关键词
            missing = []
            for keyword in test['expected_keywords']:
                if keyword not in response.processed:
                    missing.append(keyword)

            if missing:
                print(f"\n⚠️  未找到关键词: {', '.join(missing)}")
            else:
                print(f"\n✅ 所有关键词都找到了")

        except Exception as e:
            print(f"\n❌ 错误: {e}")


async def test_ai_processor():
    """测试 AI 处理器"""
    print("=" * 60)
    print("AI 文本后处理测试")
    print("=" * 60)

    # 显示当前配置
    print(f"\n📋 当前配置（从 .env 读取）:")
    print(f"   AI_PROVIDER: {settings.AI_PROVIDER}")
    print(f"   ENABLE_AI_POSTPROCESS: {settings.ENABLE_AI_POSTPROCESS}")

    # 收集可用的提供商
    available_providers = []

    # 检查 OpenAI
    if settings.OPENAI_API_KEY:
        available_providers.append(("openai", settings.OPENAI_MODEL))
        if settings.OPENAI_BASE_URL:
            print(f"\n✅ OpenAI 已配置（使用代理商: {settings.OPENAI_BASE_URL}）")
        else:
            print(f"\n✅ OpenAI 已配置")
    else:
        print(f"\n⚠️  未设置 OPENAI_API_KEY，跳过 OpenAI 测试")

    # 检查 Gemini
    if settings.GEMINI_API_KEY:
        available_providers.append(("gemini", settings.GEMINI_MODEL))
        print(f"✅ Gemini 已配置")
    else:
        print(f"⚠️  未设置 GEMINI_API_KEY，跳过 Gemini 测试")

    # 检查 Ollama
    import requests
    try:
        response = requests.get(settings.OLLAMA_BASE_URL + "/api/tags", timeout=2)
        available_providers.append(("ollama", settings.OLLAMA_MODEL))
        print(f"✅ Ollama 服务运行正常 @ {settings.OLLAMA_BASE_URL}")
    except Exception:
        print(f"⚠️  Ollama 服务未运行 @ {settings.OLLAMA_BASE_URL}，跳过 Ollama 测试")

    if not available_providers:
        print("\n❌ 错误: 没有可用的 AI 提供商")
        print("\n请在 PythonService/.env 文件中配置至少一个提供商:")
        print("  OPENAI_API_KEY=sk-xxx")
        print("  GEMINI_API_KEY=xxx")
        print("  或启动 Ollama: ollama serve &")
        return

    # 创建处理器
    processor = AIPostProcessor()

    # 测试每个可用的提供商
    for provider, model in available_providers:
        await test_provider(processor, provider, model)

    print(f"\n{'=' * 60}")
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_ai_processor())
