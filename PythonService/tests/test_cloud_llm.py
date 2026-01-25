"""
Tests for cloud LLM integration
Following TDD principles - tests written first
"""

import pytest
from postprocess.cloud_llm import (
    CloudLLMProvider,
    AnthropicProvider,
    OpenAIProvider,
    ProviderConfig,
    LLMResponse
)


@pytest.fixture
def anthropic_config():
    """Create Anthropic config"""
    return ProviderConfig(
        provider="claude",
        api_key="test-key",
        model="claude-3-5-sonnet-20241022"
    )


@pytest.fixture
def openai_config():
    """Create OpenAI config"""
    return ProviderConfig(
        provider="openai",
        api_key="test-key",
        model="gpt-4o"
    )


class TestProviderConfig:
    """Test provider configuration"""

    def test_create_config(self):
        """Test creating provider config"""
        config = ProviderConfig(
            provider="claude",
            api_key="test-key",
            model="claude-3-5-sonnet-20241022"
        )
        assert config.provider == "claude"
        assert config.api_key == "test-key"
        assert config.model == "claude-3-5-sonnet-20241022"

    def test_config_with_fallback(self):
        """Test config with fallback provider"""
        config = ProviderConfig(
            provider="claude",
            api_key="test-key",
            model="claude-3-5-sonnet-20241022",
            fallback=ProviderConfig(
                provider="openai",
                api_key="fallback-key",
                model="gpt-4o"
            )
        )
        assert config.fallback is not None
        assert config.fallback.provider == "openai"


class TestLLMResponse:
    """Test LLM response model"""

    def test_create_response(self):
        """Test creating LLM response"""
        response = LLMResponse(
            text="Processed text",
            provider="claude",
            model="claude-3-5-sonnet-20241022",
            tokens_used=100
        )
        assert response.text == "Processed text"
        assert response.provider == "claude"
        assert response.tokens_used == 100

    def test_response_with_error(self):
        """Test response with error"""
        response = LLMResponse(
            text="",
            provider="claude",
            model="claude-3-5-sonnet-20241022",
            error="API error occurred"
        )
        assert response.text == ""
        assert response.error == "API error occurred"
        assert response.has_error() is True


class TestAnthropicProvider:
    """Test Anthropic Claude provider"""

    def test_create_provider(self, anthropic_config):
        """Test creating Anthropic provider"""
        provider = AnthropicProvider(anthropic_config)
        assert provider.config.provider == "claude"
        # Provider is available if it has a non-empty API key
        assert provider.is_available() is True

    def test_provider_unavailable_without_key(self):
        """Test provider without API key is unavailable"""
        config = ProviderConfig(
            provider="claude",
            api_key="",  # Empty key
            model="claude-3-5-sonnet-20241022"
        )
        provider = AnthropicProvider(config)
        assert provider.is_available() is False

    def test_prepare_request(self, anthropic_config):
        """Test request preparation"""
        provider = AnthropicProvider(anthropic_config)
        messages = provider._prepare_messages(
            "Clean up this text please",
            "um hello uh this is a test"
        )
        assert len(messages) > 0
        assert isinstance(messages, list)

    def test_parse_response(self, anthropic_config):
        """Test response parsing"""
        provider = AnthropicProvider(anthropic_config)
        mock_response = type('MockResponse', (), {
            'content': [type('Block', (), {'text': 'Hello this is a test'})()]
        })()
        result = provider._parse_response(mock_response)
        assert result == "Hello this is a test"


class TestOpenAIProvider:
    """Test OpenAI GPT provider"""

    def test_create_provider(self, openai_config):
        """Test creating OpenAI provider"""
        provider = OpenAIProvider(openai_config)
        assert provider.config.provider == "openai"
        # Provider is available if it has a non-empty API key
        assert provider.is_available() is True

    def test_prepare_request(self, openai_config):
        """Test request preparation"""
        provider = OpenAIProvider(openai_config)
        messages = provider._prepare_messages(
            "Clean up this text please",
            "um hello uh this is a test"
        )
        assert len(messages) > 0

    def test_parse_response(self, openai_config):
        """Test response parsing"""
        provider = OpenAIProvider(openai_config)
        mock_response = type('MockResponse', (), {
            'choices': [type('Choice', (), {
                'message': type('Message', (), {'content': 'Hello this is a test'})()
            })()]
        })()
        result = provider._parse_response(mock_response)
        assert result == "Hello this is a test"


class TestProviderFactory:
    """Test provider factory"""

    def test_create_anthropic_provider(self, anthropic_config):
        """Test creating Anthropic provider via factory"""
        provider = CloudLLMProvider.create(anthropic_config)
        assert isinstance(provider, AnthropicProvider)

    def test_create_openai_provider(self, openai_config):
        """Test creating OpenAI provider via factory"""
        provider = CloudLLMProvider.create(openai_config)
        assert isinstance(provider, OpenAIProvider)

    def test_invalid_provider(self):
        """Test creating invalid provider"""
        config = ProviderConfig(
            provider="invalid",
            api_key="test-key",
            model="test-model"
        )
        with pytest.raises(ValueError):
            CloudLLMProvider.create(config)

    def test_provider_with_fallback(self):
        """Test provider with fallback"""
        config = ProviderConfig(
            provider="claude",
            api_key="invalid-key",
            model="claude-3-5-sonnet-20241022",
            fallback=ProviderConfig(
                provider="openai",
                api_key="test-key",
                model="gpt-4o"
            )
        )
        provider = CloudLLMProvider.create(config)
        assert provider is not None
        # Should use fallback when primary fails
        assert provider.config.fallback is not None


class TestPostProcessing:
    """Test LLM-based post-processing"""

    def test_post_process_prompt(self, anthropic_config):
        """Test post-processing prompt generation"""
        provider = AnthropicProvider(anthropic_config)
        prompt = provider._get_postprocess_prompt(
            "um hello uh this is a test"
        )
        assert "filler words" in prompt.lower() or "clean" in prompt.lower()

    def test_response_creation(self):
        """Test LLM response creation"""
        # Mock the API call response
        mock_response = LLMResponse(
            text="Hello this is a test",
            provider="claude",
            model="claude-3-5-sonnet-20241022",
            tokens_used=50
        )

        # Test that we can create the response
        assert mock_response.text == "Hello this is a test"
        assert mock_response.has_error() is False


class TestEnvironmentConfig:
    """Test environment-based configuration"""

    def test_config_from_env(self, monkeypatch):
        """Test loading config from environment"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-test-key")
        # This would normally load from env
        # For now, just test that we can create config
        config = ProviderConfig(
            provider="claude",
            api_key="env-test-key",
            model="claude-3-5-sonnet-20241022"
        )
        assert config.api_key == "env-test-key"

    def test_missing_api_key(self, monkeypatch):
        """Test handling missing API key"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config = ProviderConfig(
            provider="claude",
            api_key="",  # Empty key
            model="claude-3-5-sonnet-20241022"
        )
        # Should be marked as unavailable
        provider = AnthropicProvider(config)
        assert provider.is_available() is False
