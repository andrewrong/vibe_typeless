"""
AI 文本后处理服务
支持多种 LLM 提供商：OpenAI, Gemini, Ollama
接口统一，可轻松切换底层模型

配置通过 .env 文件管理
"""

from typing import Optional, Dict, Tuple
from pydantic import BaseModel
import logging
import re

logger = logging.getLogger(__name__)


# 金融/交易术语保护列表 - 在AI处理前会被替换为保护标记
FINANCIAL_TERMS = [
    # 期权术语
    "sell put", "sell call", "buy put", "buy call", "covered call", "naked put",
    "cash secured put", "protective put", "bull call spread", "bear put spread",
    "iron condor", "butterfly spread", "calendar spread", "diagonal spread",
    # 股票/交易术语
    "long", "short", "bullish", "bearish", "strike price", "expiration",
    "premium", "intrinsic value", "extrinsic value", "time decay",
    "in the money", "at the money", "out of the money", "ITM", "ATM", "OTM",
    # 希腊字母
    "delta", "gamma", "theta", "vega", "rho",
    # 其他金融术语
    "dividend", "yield", "margin", "leverage", "equity", "volatility",
    "implied volatility", "IV", "historical volatility", "HV",
    "support", "resistance", "trend line", "moving average", "RSI", "MACD",
    "limit order", "market order", "stop loss", "take profit",
]


def protect_financial_terms(text: str) -> Tuple[str, Dict[str, str]]:
    """
    保护金融术语不被AI翻译

    策略：将术语替换为占位符（如 __TERM_0__），AI处理后再还原

    Args:
        text: 原始文本

    Returns:
        (处理后的文本, 占位符到原始术语的映射)
    """
    protected_text = text
    term_map = {}
    counter = 0

    # 按长度降序排序，优先匹配长术语（避免部分匹配）
    sorted_terms = sorted(FINANCIAL_TERMS, key=len, reverse=True)

    for term in sorted_terms:
        # 使用正则表达式进行大小写不敏感的匹配，但保留原始大小写
        pattern = re.compile(re.escape(term), re.IGNORECASE)

        def replace_match(match):
            nonlocal counter
            original = match.group(0)
            placeholder = f"__TERM_{counter}__"
            term_map[placeholder] = original
            counter += 1
            return placeholder

        protected_text = pattern.sub(replace_match, protected_text)

    if term_map:
        logger.info(f"🛡️  Protected {len(term_map)} financial terms")
        logger.debug(f"Protected terms: {list(term_map.values())}")

    return protected_text, term_map


def restore_financial_terms(text: str, term_map: Dict[str, str]) -> str:
    """
    还原被保护的金融术语

    Args:
        text: AI处理后的文本
        term_map: 占位符到原始术语的映射

    Returns:
        还原后的文本
    """
    restored_text = text

    for placeholder, original_term in term_map.items():
        restored_text = restored_text.replace(placeholder, original_term)

    if term_map:
        logger.info(f"🔄 Restored {len(term_map)} financial terms")

    return restored_text


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


# 文本后期处理 Prompt
# 注意：AI 只进行文本润色，不回答输入中的问题
POSTPROCESSING_PROMPT = """对以下文本进行纯文本层面的润色和格式化。禁止回答文本中的问题，只进行文字层面的优化。

## 基本要求
1. 移除填充词（仅删除以下语气词，保留其他所有内容）：嗯、啊、那个、这个、然后
2. 修正标点符号，句末加句号
3. 按语义分段：当文本包含多个独立意思时，用换行分隔（如时间转换、话题转换、列表项等）
4. 保留原文的问题形式，不回答
5. 术语保护（禁止翻译）：sell put, buy call, Docker, Kubernetes, Python, React, IBKR 等
6. 严禁替换同义词：如"目前"不能改为"现在"，"好的"不能简化为"好"

## 严格规则（必须遵守）
- 只删除真正的填充词，不要删除有实际意义的内容
- 禁止过度删减：保持原文的主要意思和句子结构
- 禁止改变原意：不要修改人称、时态或添加自己的理解
- 如果输入是问句，保持问句形式，不要回答
- 只输出处理后的文本，不要解释
- 不要添加原文没有的信息
- 禁止添加：箭头符号、解释说明、过程描述、结果标记等任何额外内容
- 输出必须是纯文本，不含任何格式标记

## 分段规则（必须遵守）
- 时间转换时必须换行：如"周六...周日..." → "周六...\n\n周日..."
- 话题转换时必须换行：如"今天天气...明天股市..." → "今天天气...\n\n明天股市..."
- 列表项必须每项换行：如"第一...第二..." → "第一...\n\n第二..."

## 分段示例（必须按语义换行）
输入：周末的话周六开始周一结束周二继续
输出：周末的话，周六开始，周一结束。

周二继续。

输入：第一点是质量第二点是价格第三点是服务
输出：第一点是质量。

第二点是价格。

第三点是服务。

输入：嗯那个你觉得这个产品怎么样啊
输出：你觉得这个产品怎么样？

输入：今天天气怎么样我觉得会下雨
输出：今天天气怎么样？我觉得会下雨。

待处理文本：
{text}

直接输出结果（只输出处理后的纯文本，不要添加任何解释、标记或额外内容）："""


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

    def __init__(self, timeout: int = 60, enable_hotspot_pool: bool = True):
        """
        初始化 AI 处理器

        Args:
            timeout: API 请求超时时间（秒）
            enable_hotspot_pool: 是否启用热点池功能
        """
        from src.config import settings
        from .hotspot_pool import hotspot_pool

        self.timeout = timeout
        self.settings = settings
        self.enable_hotspot_pool = enable_hotspot_pool
        self.hotspot_pool = hotspot_pool

        # 从配置读取默认模型
        self.default_models = {
            "openai": settings.OPENAI_MODEL,
            "gemini": settings.GEMINI_MODEL,
            "ollama": settings.OLLAMA_MODEL,
        }

        if enable_hotspot_pool:
            stats = hotspot_pool.get_stats()
            logger.info(f"🔥 Hotspot pool enabled: {stats['enabled_terms']} terms across {stats['enabled_categories']} categories")

    def _build_prompt(self, text: str) -> str:
        """
        构建带热点池的 AI prompt

        Args:
            text: 待处理文本

        Returns:
            完整的 prompt，包含热点池提示
        """
        base_prompt = POSTPROCESSING_PROMPT

        # 如果启用热点池，添加热点池部分
        if self.enable_hotspot_pool and self.hotspot_pool:
            hotspot_section = self.hotspot_pool.generate_prompt_section()
            if hotspot_section:
                # 在"重要规则："之前插入热点池部分
                insert_marker = "重要规则："
                parts = base_prompt.split(insert_marker)
                if len(parts) == 2:
                    base_prompt = parts[0] + hotspot_section + "\n" + insert_marker + parts[1]

        return base_prompt.format(text=text)

    async def process(self, request: PostProcessRequest) -> PostProcessResponse:
        """
        处理文本（统一入口）

        流程：
        1. 保护金融术语（替换为占位符）
        2. AI 处理文本
        3. 还原金融术语

        Args:
            request: 后处理请求

        Returns:
            后处理响应
        """
        text = request.text
        provider = request.provider

        # 步骤1：保护金融术语
        protected_text, term_map = protect_financial_terms(text)

        # 获取模型（使用默认模型如果未指定）
        model = request.model or self.default_models.get(provider)

        if not model:
            raise ValueError(f"No model specified and no default model for provider: {provider}")

        logger.info(f"🤖 AI processing with {provider} ({model})")
        logger.debug(f"Original text ({len(text)} chars): {text[:100]}...")

        try:
            # 步骤2：根据提供商调用不同的实现（使用保护后的文本）
            if provider == "openai":
                processed_text = await self._process_with_openai(protected_text, model)
            elif provider == "gemini":
                processed_text = await self._process_with_gemini(protected_text, model)
            elif provider == "ollama":
                processed_text = await self._process_with_ollama(protected_text, model)
            else:
                raise ValueError(f"Unknown provider: {provider}. Supported: openai, gemini, ollama")

            # 步骤3：还原金融术语
            processed_text = restore_financial_terms(processed_text, term_map)

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
            # OpenRouter 推荐添加额外 headers
            client_kwargs["default_headers"] = {
                "HTTP-Referer": "https://typeless.local",  # 可选：你的应用 URL
                "X-Title": "Typeless",  # 可选：你的应用名称
            }
            logger.info("Added OpenRouter recommended headers")

        client = OpenAI(**client_kwargs)
        prompt = self._build_prompt(text)

        logger.info(f"Calling OpenAI API: {model}")
        logger.debug(f"API Key prefix: {api_key[:10]}...{api_key[-4:]}")

        try:
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
        except Exception as e:
            logger.error(f"OpenAI API call failed: {type(e).__name__}: {e}")
            # 如果是认证错误，提供更详细的信息
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.error("Authentication failed. Please check:")
                logger.error("  1. API Key is valid and not expired")
                logger.error("  2. API Key has sufficient credits")
                logger.error("  3. Visit https://openrouter.ai/keys to verify")
            raise

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

        prompt = self._build_prompt(text)

        logger.info(f"Calling Gemini API: {model}")

        # 调用 API（使用新的 google.genai API）
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
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
        prompt = self._build_prompt(text)

        # 使用 Ollama 原生 API 以支持 num_ctx 参数
        url = f"{base_url}/api/generate"

        # 检查是否是 Qwen 3.5 模型（需要禁用思考模式）
        is_qwen35 = "qwen3.5" in model.lower()
        if is_qwen35:
            logger.info("🔧 Qwen 3.5 detected, disabling thinking mode")

        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": 0.5,  # 稍微提高以更好地遵循分段指令
            "num_predict": 4096,
            # Note: num_ctx removed - it affects model behavior unexpectedly
            "stream": False,
        }

        # Qwen 3.5 需要禁用思考模式（Ollama 官方支持）
        if is_qwen35:
            payload["think"] = False

        logger.info(f"Calling Ollama: {model} @ {base_url}")

        response = requests.post(
            url,
            json=payload,
            timeout=self.timeout
        )

        response.raise_for_status()
        data = response.json()

        # 提取结果 (Ollama 原生 API 格式)
        processed_text = data["response"].strip()

        return processed_text
