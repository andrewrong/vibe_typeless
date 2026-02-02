"""
验证 Gemini 是否真的被调用
"""
import asyncio
import sys
import logging
sys.path.insert(0, '.')

# 设置详细日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

from src.postprocess.ai_processor import AIPostProcessor, PostProcessRequest

async def test():
    processor = AIPostProcessor()

    test_text = "嗯 那个 五个 事情"

    print("=" * 60)
    print("验证 Gemini API 调用")
    print("=" * 60)
    print(f"\n原始文本: {test_text}")

    request = PostProcessRequest(
        text=test_text,
        provider="gemini",
        model="gemini-3-flash-preview"
    )

    print("\n开始处理...")
    response = await processor.process(request)

    print(f"\n优化后文本: {response.processed}")
    print(f"使用的提供商: {response.provider}")
    print(f"使用的模型: {response.model}")
    print("\n" + "=" * 60)

asyncio.run(test())
