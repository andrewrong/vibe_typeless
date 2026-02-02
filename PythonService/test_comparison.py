"""
AI 处理前后对比测试
展示规则引擎 vs AI 处理的效果差异
"""
import asyncio
import sys
sys.path.insert(0, '.')

from src.postprocess.ai_processor import AIPostProcessor, PostProcessRequest
from src.postprocess.processor import TextProcessor

# 测试用例
test_cases = [
    {
        "name": "移除填充词 + 数字转换 + 列表格式化",
        "input": "嗯 那个 五个 事情 首先 我们需要 做 API 接口 设计 然后 实现 它 最后 测试 它"
    },
    {
        "name": "数字转换（中文数字 → 阿拉伯数字）",
        "input": "我买了 三个 iPhone 和 二十 美元的配件"
    },
    {
        "name": "列表格式化",
        "input": "要做三件事 第一 编写代码 第二 测试 第三 部署"
    },
    {
        "name": "中英文混合 + 技术术语",
        "input": "我们在 GitHub 上找到 Docker 镜像 然后 下载 它"
    },
    {
        "name": "去除重复",
        "input": "你好 你好 我想 我想 说 去商店"
    },
    {
        "name": "段落组织",
        "input": "这是一个很长的文本包含很多内容需要分成多个段落来提高可读性应该有更好的结构"
    },
]

async def compare():
    """对比规则引擎和 AI 处理"""
    print("=" * 80)
    print("AI 处理前后对比测试")
    print("=" * 80)
    print(f"\n使用模型: gemini-3-flash-preview")
    print("=" * 80)

    # 创建处理器
    ai_processor = AIPostProcessor()
    rule_processor = TextProcessor()

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"测试 {i}/{len(test_cases)}: {test['name']}")
        print('=' * 80)

        original = test['input']
        print(f"\n📝 原始文本:")
        print(f"   {original}")
        print(f"   长度: {len(original)} 字符")

        # 规则引擎处理
        print(f"\n🔧 规则引擎处理:")
        rule_result = rule_processor.process(original)
        print(f"   {rule_result.processed}")
        print(f"   长度: {len(rule_result.processed)} 字符")
        print(f"   变化: {len(rule_result.processed) - len(original):+d} 字符")

        # AI 处理
        print(f"\n🤖 AI 处理 (Gemini):")
        try:
            ai_request = PostProcessRequest(
                text=original,
                provider="gemini",
                model="gemini-3-flash-preview"
            )
            ai_result = await ai_processor.process(ai_request)
            print(f"   {ai_result.processed}")
            print(f"   长度: {len(ai_result.processed)} 字符")
            print(f"   变化: {len(ai_result.processed) - len(original):+d} 字符")

            # 对比差异
            if rule_result.processed != ai_result.processed:
                print(f"\n✨ AI 额外优化:")
                if "5" in ai_result.processed and "五" in original and "5" not in rule_result.processed:
                    print("   ✅ 数字转换: 五 → 5")
                if any(keyword in ai_result.processed for keyword in ["1.", "2.", "3."]) and not any(keyword in rule_result.processed for keyword in ["1.", "2.", "3."]):
                    print("   ✅ 列表格式化: 自动添加序号")
                if len(ai_result.processed) < len(rule_result.processed):
                    print(f"   ✅ 更简洁: 比规则引擎少 {len(rule_result.processed) - len(ai_result.processed)} 字符")
        except Exception as e:
            print(f"   ❌ 错误: {e}")

    print(f"\n{'=' * 80}")
    print("测试完成")
    print("=" * 80)

asyncio.run(compare())
