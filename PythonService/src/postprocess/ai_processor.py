"""
AI 文本后处理服务
支持多种 LLM 提供商：OpenAI, Gemini, Ollama
接口统一，可轻松切换底层模型

配置通过 .env 文件管理
"""

from typing import Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class PostProcessRequest(BaseModel):
    """后处理请求"""
    text: str
    provider: str = "openai"  # openai, gemini, ollama
    model: Optional[str] = None  # None = 使用默认模型


class PostProcessResponse(BaseModel):
    """后处理响应"""
    original: str
    processed: str
    provider: str
    model: Optional[str] = None


# 优化后的 Prompt（支持中英文混合）
POSTPROCESSING_PROMPT = """你是一个专业的文本编辑助手。请清理和优化以下语音转录文本，使其更加清晰流畅。

## 基本要求
- 清理文本使其更自然流畅，保持原意和语气
- 修复明显的语法错误，移除填充词（嗯、啊、那个）和口吃
- 去除重复内容（包括词语和句子的重复）
- 保留专有名词、人名、数字和技术术语
- 根据文本语境决定使用正式或非正式语体

## 格式要求
- **列表格式**：自动检测并正确格式化列表
  - 有序列表：提到数字（如"3件事"、"5个"）、序数词（首先、其次）、步骤、序列或编号的内容
  - 无序列表：其他列举性质的内容
  - 每个列表项单独成行

- **数字转换**：将文字形式的数字转换为阿拉伯数字
  - 例："五" → "5"、"二十美元" → "$20"、"百分之五十" → "50%"
  - 保留电话号码、日期等已有数字格式

- **段落组织**：将长文本分成 2-4 句的短段落，提高可读性
  - 按主题或逻辑分段
  - 避免单个段落过长或过短

- **标点符号**：使用正确的中文标点符号
  - 句末使用句号（。）
  - 疑问句使用问号（？）
  - 感叹句使用感叹号（！）
  - 列表项末尾不加标点

## 语言处理
- **主要语言**：识别文本的主要语言（中文或英文）
- **混合文本**：如果中英文混合，保持原有的混合方式
- **技术术语**：保留英文术语（如 API、GitHub、Docker 等）不翻译
- **代码和命令**：保持原样，不格式化

## 禁止事项
- ❌ 不要添加任何原文中没有的信息
- ❌ 不要添加解释、标签、元数据或说明文字
- ❌ 不要改变原文的观点和意图
- ❌ 不要输出"以下是处理后的文本"这类引导语
- ❌ 不要添加标题或章节标记

## 输出格式
**只输出处理后的文本，不要有任何其他内容。**

---
待处理文本：
<TRANSCRIPT>
{text}
</TRANSCRIPT>
"""


class AIPostProcessor:
    """
    AI 文本后处理器 - 统一接口，支持多种提供商

    支持的提供商：
    - openai: GPT-4o, GPT-4o-mini, etc. (支持自定义 base_url)
    - gemini: Gemini Pro, Gemini Flash, etc.
    - ollama: 本地模型（可选）

    使用示例：
        processor = AIPostProcessor()

        # 使用 OpenAI
        response = await processor.process(PostProcessRequest(
            text="嗯 那个 五个 事情",
            provider="openai",
            model="gpt-4o-mini"  # 或 None 使用默认
        ))

        # 使用 Gemini
        response = await processor.process(PostProcessRequest(
            text="嗯 那个 五个 事情",
            provider="gemini",
            model="gemini-2.0-flash-exp"  # 或 None 使用默认
        ))
    """

    def __init__(self, timeout: int = 60):
        """
        初始化 AI 处理器

        Args:
            timeout: API 请求超时时间（秒）
        """
        from src.config import settings

        self.timeout = timeout
        self.settings = settings

        # 从配置读取默认模型
        self.default_models = {
            "openai": settings.OPENAI_MODEL,
            "gemini": settings.GEMINI_MODEL,
            "ollama": settings.OLLAMA_MODEL,
        }

    async def process(self, request: PostProcessRequest) -> PostProcessResponse:
        """
        处理文本（统一入口）

        Args:
            request: 后处理请求

        Returns:
            后处理响应
        """
        text = request.text
        provider = request.provider

        # 获取模型（使用默认模型如果未指定）
        model = request.model or self.default_models.get(provider)

        if not model:
            raise ValueError(f"No model specified and no default model for provider: {provider}")

        logger.info(f"🤖 AI processing with {provider} ({model})")
        logger.debug(f"Original text ({len(text)} chars): {text[:100]}...")

        try:
            # 根据提供商调用不同的实现
            if provider == "openai":
                processed_text = await self._process_with_openai(text, model)
            elif provider == "gemini":
                processed_text = await self._process_with_gemini(text, model)
            elif provider == "ollama":
                processed_text = await self._process_with_ollama(text, model)
            else:
                raise ValueError(f"Unknown provider: {provider}. Supported: openai, gemini, ollama")

            logger.info(f"✅ AI processing complete ({len(processed_text)} chars)")
            logger.debug(f"Processed text: {processed_text[:100]}...")

            return PostProcessResponse(
                original=text,
                processed=processed_text,
                provider=provider,
                model=model
            )
        except Exception as e:
            logger.error(f"❌ AI processing failed: {e}")
            raise

    async def _process_with_openai(self, text: str, model: str) -> str:
        """
        使用 OpenAI API 处理文本

        Args:
            text: 待处理文本
            model: 模型名称（如 gpt-4o, gpt-4o-mini, gpt-3.5-turbo）

        Returns:
            处理后的文本

        Raises:
            ValueError: OPENAI_API_KEY 未设置
        """
        api_key = self.settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in .env file. "
                "Add it to .env: OPENAI_API_KEY=sk-xxx"
            )

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI SDK not installed. "
                "Install with: uv add openai"
            )

        # 创建客户端，支持自定义 base_url（中间代理商）
        client_kwargs = {"api_key": api_key}
        if self.settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = self.settings.OPENAI_BASE_URL
            logger.info(f"Using custom OpenAI base_url: {self.settings.OPENAI_BASE_URL}")

        client = OpenAI(**client_kwargs)
        prompt = POSTPROCESSING_PROMPT.format(text=text)

        logger.info(f"Calling OpenAI API: {model}")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=4096
        )

        processed_text = response.choices[0].message.content.strip()
        return processed_text

    async def _process_with_gemini(self, text: str, model: str) -> str:
        """
        使用 Gemini API 处理文本

        Args:
            text: 待处理文本
            model: 模型名称（如 gemini-2.0-flash-exp, gemini-exp-1206）

        Returns:
            处理后的文本

        Raises:
            ValueError: GEMINI_API_KEY 未设置
        """
        api_key = self.settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in .env file. "
                "Add it to .env: GEMINI_API_KEY=xxx"
            )

        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "Google Gen AI SDK not installed. "
                "Install with: uv add google-genai"
            )

        # 创建客户端
        client = genai.Client(api_key=api_key)

        prompt = POSTPROCESSING_PROMPT.format(text=text)

        logger.info(f"Calling Gemini API: {model}")

        # 调用 API（使用新的 generate_content API）
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=genai.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=4096,
            )
        )

        processed_text = response.text.strip()
        return processed_text

    async def _process_with_ollama(self, text: str, model: str) -> str:
        """
        使用 Ollama API 处理文本（本地 LLM）

        Args:
            text: 待处理文本
            model: 模型名称（如 qwen2.5:7b, llama3:8b, phi3:mini）

        Returns:
            处理后的文本
        """
        import requests

        base_url = self.settings.OLLAMA_BASE_URL
        prompt = POSTPROCESSING_PROMPT.format(text=text)

        # 调用 Ollama API（OpenAI 兼容格式）
        url = f"{base_url}/v1/chat/completions"

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 4096
        }

        logger.info(f"Calling Ollama: {model} @ {base_url}")

        response = requests.post(
            url,
            json=payload,
            timeout=self.timeout
        )

        response.raise_for_status()
        data = response.json()

        # 提取结果
        processed_text = data["choices"][0]["message"]["content"].strip()

        return processed_text
