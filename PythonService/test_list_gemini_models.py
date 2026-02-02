"""
查询可用的 Gemini 模型列表
"""
import sys
sys.path.insert(0, '.')

from src.config import settings

if not settings.GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY 未设置")
    sys.exit(1)

import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)

print("正在查询可用的 Gemini 模型...\n")

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✅ {model.name}")
        print(f"   显示名称: {model.display_name}")
        print(f"   描述: {model.description}")
        print()
