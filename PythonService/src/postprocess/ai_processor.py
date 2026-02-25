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


# 优化后的 Prompt（支持中英文混合）
POSTPROCESSING_PROMPT = """清理和优化语音转录文本。直接输出结果，不要添加任何引言或解释。

## 基本要求（必须严格执行）
- 清理文本使其更自然流畅，保持原意和语气
- 修复明显的语法错误，移除填充词（嗯、啊、那个）和口吃
- 去除重复内容（包括词语和句子的重复）
- 保留专有名词、人名、数字和技术术语
- 根据文本语境决定使用正式或非正式语体

## 格式规范（必须严格执行）

### 分段规则（非常重要）
- **必须**将长文本按逻辑分成多个短段落
- 每个段落包含 2-4 句话
- 段落之间用空行分隔
- 按主题、时间或逻辑关系分段
- 避免大段文字不分段

### 标点符号规则（非常重要）
- **必须**使用正确的中文标点符号
- 句末必须使用句号（。）
- 疑问句使用问号（？）
- 感叹句使用感叹号（！）
- 列表项末尾不加标点
- 引号使用 "" 或 ''
- 括号使用（）

### 列表格式
- **列表格式**：自动检测并正确格式化列表
  - 有序列表：提到数字（如"3件事"、"5个"）、序数词（首先、其次）、步骤、序列或编号的内容
  - 无序列表：其他列举性质的内容
  - 每个列表项单独成行

- **数字转换**：将文字形式的数字转换为阿拉伯数字
  - 例："五" → "5"、"二十美元" → "$20"、"百分之五十" → "50%"
  - 保留电话号码、日期等已有数字格式


## 术语保护（最高优先级 - 必须严格执行）

### 🔴 绝对禁止翻译以下术语
以下英文术语必须**原样保留**，**禁止**翻译为中文，**禁止**改写，**禁止**解释：

**金融术语（保持英文）：**
sell put, sell call, buy put, buy call, covered call, naked put, cash secured put, iron condor, butterfly spread, straddle, strangle, long, short, bullish, bearish, strike price, expiration, premium, ITM, ATM, OTM, delta, gamma, theta, vega, rho, ETF, REITs, IPO, CPI, PPI, GDP, PMI, dividend, yield, margin, leverage, volatility, IV

**技术术语（保持英文）：**
Python, JavaScript, TypeScript, Swift, Rust, Go, Java, C++, C#, React, Vue, Angular, Docker, Kubernetes, K8s, Git, GitHub, GitLab, AWS, Azure, GCP, Vercel, Netlify, API, CI/CD, DevOps, SQL, NoSQL, JSON, YAML, REST, GraphQL

### 🔴 术语映射规则（必须遵循）
| 原文中的音译/近似音 | 必须替换为 |
|---------------------|-----------|
| 卖扑、赛普、塞普 | sell put |
| 买考、买科、麦考 | buy call |
| 卖考、卖科 | sell call |
| 买扑、买普 | buy put |
| docker | Docker |
| k8s、K8s | Kubernetes |
| github | GitHub |

### 术语处理对照
- 卖出看跌期权策略 → sell put 策略
- 买入看涨期权 → buy call
- python 和 react → Python 和 React

## 语言处理
- **主要语言**：识别文本的主要语言（中文或英文）
- **混合文本**：如果中英文混合，保持原有的混合方式
- **代码和命令**：保持原样，不格式化

## 禁止事项
- ❌ 不要添加任何原文中没有的信息
- ❌ 不要添加解释、标签、元数据或说明文字
- ❌ 不要改变原文的观点和意图
- ❌ 不要输出"以下是处理后的文本"这类引导语
- ❌ 不要添加标题或章节标记

## 待处理文本（只输出处理后的纯文本）
{text}
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
                # 在基本要求后面插入热点池部分
                insert_marker = "## 基本要求"
                parts = base_prompt.split(insert_marker)
                if len(parts) == 2:
                    base_prompt = parts[0] + insert_marker + parts[1].split("\n")[0] + "\n" + hotspot_section + "\n" + "\n".join(parts[1].split("\n")[1:])

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
