"""
测试完整的转录流程，找出标点符号问题
"""
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')

from src.api.routes import processor, personal_dictionary
from src.postprocess.punctuation import ChinesePunctuationCorrector

# 测试文本
test_text = "現在正在寫代碼是一個用AI生成的語音識別的功能"

print("=" * 60)
print("测试转录后处理流程")
print("=" * 60)

print(f"\n1️⃣ 原始转录文本:")
print(f"   {test_text!r}")

# 测试标点符号纠正
print(f"\n2️⃣ 应用标点符号纠正:")
corrector = processor.punctuation_corrector
result_punct = corrector.correct(test_text)
print(f"   {result_punct!r}")

# 测试个人词典
print(f"\n3️⃣ 应用个人词典:")
result_dict = personal_dictionary.apply(result_punct)
print(f"   {result_dict!r}")

print("\n" + "=" * 60)
