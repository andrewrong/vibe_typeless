"""
简单测试 AI 文本优化
"""
import asyncio
import sys
sys.path.insert(0, '.')

from src.postprocess.ai_processor import AIPostProcessor, PostProcessRequest

async def test():
    processor = AIPostProcessor()

    test_text = "嗯 那个 五个 事情 首先 我们需要 做 API 接口 设计 然后 实现 它 最后 测试 它"

    print("=" * 60)
    print("AI 文本优化测试 (gemini-3-flash-preview)")
    print("=" * 60)
    print(f"\n原始文本:\n{test_text}")

    request = PostProcessRequest(
        text=test_text,
        provider="gemini",
        model="gemini-3-flash-preview"
    )

    response = await processor.process(request)

    print(f"\n优化后文本:\n{response.processed}")
    print("\n" + "=" * 60)

asyncio.run(test())
