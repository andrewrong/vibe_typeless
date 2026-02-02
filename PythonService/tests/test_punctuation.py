"""
测试中文标点符号纠正功能
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.postprocess.punctuation import ChinesePunctuationCorrector


def test_question_detection():
    """测试问句识别"""
    corrector = ChinesePunctuationCorrector()

    # 测试用例
    test_cases = [
        # (输入, 期望输出)
        ("你怎么看这个问题", "你怎么看这个问题？"),  # 怎么
        ("这是什么", "这是什么？"),  # 什么
        ("为什么要这样做", "为什么要这样做？"),  # 为什么
        ("他叫什么名字", "他叫什么名字？"),  # 什么
        ("你知道怎么用吗", "你知道怎么用吗？"),  # 吗
        ("是还是不是", "是还是不是？"),  # 还是
        ("对不对", "对不对？"),  # 对不对
        ("好不好", "好不好？"),  # 好不好
    ]

    print("🧪 测试问句识别:")
    all_passed = True
    for input_text, expected in test_cases:
        result = corrector.correct(input_text)
        passed = result == expected
        all_passed = all_passed and passed
        status = "✅" if passed else f"❌ (期望: {expected})"
        print(f"  {status} '{input_text}' → '{result}'")

    return all_passed


def test_exclamation_detection():
    """测试感叹句识别"""
    corrector = ChinesePunctuationCorrector()

    test_cases = [
        ("太好了", "太好了！"),  # 太
        ("真是太棒了", "真是太棒了！"),  # 真
        ("非常好", "非常好！"),  # 非常
        ("这怎么可能", "这怎么可能？"),  # 反问句，问号也可以
    ]

    print("\n🧪 测试感叹句识别:")
    all_passed = True
    for input_text, expected in test_cases:
        result = corrector.correct(input_text)
        passed = result == expected
        all_passed = all_passed and passed
        status = "✅" if passed else f"❌ (期望: {expected})"
        print(f"  {status} '{input_text}' → '{result}'")

    return all_passed


def test_statement_detection():
    """测试陈述句"""
    corrector = ChinesePunctuationCorrector()

    test_cases = [
        ("我告诉他怎么做", "我告诉他怎么做。"),  # 告诉(陈述)优先
        ("我觉得这很好", "我觉得这很好。"),  # 觉得(陈述)
        ("他说为什么这样做", "他说为什么这样做。"),  # 说(陈述)
    ]

    print("\n🧪 测试陈述句识别:")
    all_passed = True
    for input_text, expected in test_cases:
        result = corrector.correct(input_text)
        passed = result == expected
        all_passed = all_passed and passed
        status = "✅" if passed else f"❌ (期望: {expected})"
        print(f"  {status} '{input_text}' → '{result}'")

    return all_passed


def test_multi_sentence():
    """测试多句子"""
    corrector = ChinesePunctuationCorrector()

    test_cases = [
        # 如果有连接词，应该能分割
        ("你怎么看这个问题但是我觉得很好", "你怎么看这个问题？但是我觉得很好。"),
        ("这是什么而且太好了", "这是什么？而且太好了！"),
        ("为什么这样做不过我觉得应该可以", "为什么这样做？不过我觉得应该可以。"),
    ]

    print("\n🧪 测试多句子:")
    all_passed = True
    for input_text, expected in test_cases:
        result = corrector.correct(input_text)
        passed = result == expected
        all_passed = all_passed and passed
        status = "✅" if passed else f"❌ (期望: {expected})"
        print(f"  {status} '{input_text}' → '{result}'")

    return all_passed


if __name__ == "__main__":
    print("=" * 60)
    print("中文标点符号纠正测试")
    print("=" * 60)

    results = []
    results.append(test_question_detection())
    results.append(test_exclamation_detection())
    results.append(test_statement_detection())
    results.append(test_multi_sentence())

    print("\n" + "=" * 60)
    if all(results):
        print("✅ 所有测试通过!")
    else:
        print("❌ 部分测试失败")
    print("=" * 60)
