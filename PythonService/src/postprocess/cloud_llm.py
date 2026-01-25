"""
Cloud LLM Integration Module
Provides abstraction layer for various LLM providers (Anthropic, OpenAI, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict
import os


@dataclass
class ProviderConfig:
    """Configuration for LLM provider"""
    provider: str  # "claude" or "openai"
    api_key: str
    model: str
    api_base: Optional[str] = None
    timeout: int = 30
    max_tokens: int = 1000
    temperature: float = 0.3
    fallback: Optional['ProviderConfig'] = None


@dataclass
class LLMResponse:
    """Response from LLM provider"""
    text: str
    provider: str
    model: str
    tokens_used: int = 0
    error: Optional[str] = None

    def has_error(self) -> bool:
        """Check if response contains an error"""
        return self.error is not None


class CloudLLMProvider(ABC):
    """
    Abstract base class for cloud LLM providers

    Supports:
    - Anthropic Claude
    - OpenAI GPT
    - Extensible for future providers
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize provider

        Args:
            config: Provider configuration
        """
        self.config = config
        self._client = None

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available (has valid API key)"""
        pass

    @abstractmethod
    def _create_client(self):
        """Create API client"""
        pass

    @abstractmethod
    def _prepare_messages(self, instruction: str, text: str) -> List[Dict]:
        """Prepare messages for API request"""
        pass

    @abstractmethod
    def _call_api(self, messages: List[Dict]) -> Any:
        """Call the provider API"""
        pass

    @abstractmethod
    def _parse_response(self, response: Any) -> str:
        """Parse API response to extract text"""
        pass

    def _get_postprocess_prompt(self, text: str) -> str:
        """Get the system prompt for post-processing"""
        return (
            "You are a text post-processing assistant. Your task is to clean up "
            "transcribed speech by:\n"
            "1. Removing filler words (um, uh, like, you know, etc.)\n"
            "2. Removing stutter repetitions\n"
            "3. Detecting and applying self-corrections\n"
            "4. Improving readability while preserving the original meaning\n\n"
            "Return only the cleaned text without any explanations or metadata."
        )

    def process_text(self, text: str) -> LLMResponse:
        """
        Process text using LLM

        Args:
            text: Input text to process

        Returns:
            LLMResponse with processed text or error
        """
        if not self.is_available():
            # Try fallback
            if self.config.fallback:
                fallback_provider = self.create(self.config.fallback)
                return fallback_provider.process_text(text)
            return LLMResponse(
                text=text,
                provider=self.config.provider,
                model=self.config.model,
                error="API key not available"
            )

        try:
            # Prepare messages
            system_prompt = self._get_postprocess_prompt(text)
            messages = self._prepare_messages(system_prompt, text)

            # Call API
            response = self._call_api(messages)

            # Parse response
            processed_text = self._parse_response(response)

            return LLMResponse(
                text=processed_text,
                provider=self.config.provider,
                model=self.config.model
            )

        except Exception as e:
            # Try fallback on error
            if self.config.fallback:
                fallback_provider = self.create(self.config.fallback)
                return fallback_provider.process_text(text)

            return LLMResponse(
                text=text,
                provider=self.config.provider,
                model=self.config.model,
                error=str(e)
            )

    @staticmethod
    def create(config: ProviderConfig) -> 'CloudLLMProvider':
        """
        Factory method to create provider instance

        Args:
            config: Provider configuration

        Returns:
            Provider instance
        """
        providers = {
            "claude": AnthropicProvider,
            "anthropic": AnthropicProvider,
            "openai": OpenAIProvider,
            "gpt": OpenAIProvider
        }

        provider_class = providers.get(config.provider.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider: {config.provider}")

        return provider_class(config)


class AnthropicProvider(CloudLLMProvider):
    """Anthropic Claude provider"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None

    def is_available(self) -> bool:
        """Check if Anthropic API key is available"""
        return bool(self.config.api_key and self.config.api_key != "")

    def _create_client(self):
        """Create Anthropic client"""
        try:
            from anthropic import Anthropic
            return Anthropic(api_key=self.config.api_key)
        except ImportError:
            return None

    @property
    def client(self):
        """Lazy load client"""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _prepare_messages(self, instruction: str, text: str) -> List[Dict]:
        """Prepare messages for Anthropic API"""
        return [
            {"role": "user", "content": f"{instruction}\n\nText: {text}"}
        ]

    def _call_api(self, messages: List[Dict]) -> Any:
        """Call Anthropic API"""
        if not self.client:
            raise RuntimeError("Anthropic client not available")

        return self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=messages
        )

    def _parse_response(self, response: Any) -> str:
        """Parse Anthropic response"""
        if response and hasattr(response, 'content'):
            return response.content[0].text
        return ""


class OpenAIProvider(CloudLLMProvider):
    """OpenAI GPT provider"""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None

    def is_available(self) -> bool:
        """Check if OpenAI API key is available"""
        return bool(self.config.api_key and self.config.api_key != "")

    def _create_client(self):
        """Create OpenAI client"""
        try:
            from openai import OpenAI
            kwargs = {"api_key": self.config.api_key}
            if self.config.api_base:
                kwargs["base_url"] = self.config.api_base
            return OpenAI(**kwargs)
        except ImportError:
            return None

    @property
    def client(self):
        """Lazy load client"""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _prepare_messages(self, instruction: str, text: str) -> List[Dict]:
        """Prepare messages for OpenAI API"""
        return [
            {"role": "system", "content": instruction},
            {"role": "user", "content": text}
        ]

    def _call_api(self, messages: List[Dict]) -> Any:
        """Call OpenAI API"""
        if not self.client:
            raise RuntimeError("OpenAI client not available")

        return self.client.chat.completions.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=messages
        )

    def _parse_response(self, response: Any) -> str:
        """Parse OpenAI response"""
        if response and hasattr(response, 'choices'):
            return response.choices[0].message.content
        return ""


def create_provider_from_env(
    provider: str = "claude",
    model: Optional[str] = None
) -> CloudLLMProvider:
    """
    Create provider from environment variables

    Args:
        provider: Provider name ("claude" or "openai")
        model: Model name (optional, uses default if not specified)

    Returns:
        Provider instance
    """
    # Default models
    default_models = {
        "claude": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4o"
    }

    # Get API key from env
    env_keys = {
        "claude": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY"
    }

    api_key = os.getenv(env_keys.get(provider, ""))
    if not api_key:
        api_key = ""  # Will make provider unavailable

    config = ProviderConfig(
        provider=provider,
        api_key=api_key,
        model=model or default_models.get(provider, "")
    )

    return CloudLLMProvider.create(config)
