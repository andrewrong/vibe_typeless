"""
配置管理
使用 .env 文件管理 API Keys 和其他配置
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # AI 后处理配置
    ENABLE_AI_POSTPROCESS: bool = False
    AI_PROVIDER: str = "openai"  # openai, gemini, ollama

    # OpenAI 配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None  # 支持中间代理商
    OPENAI_MODEL: str = "gpt-4o-mini"  # 默认模型

    # Gemini 配置
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3-flash-preview"  # 默认模型

    # Ollama 配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"  # 默认模型

    # 模型配置
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings
