"""
配置管理
使用 .env 文件管理 API Keys 和其他配置
.env 文件优先级高于环境变量
"""
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os


def parse_env_file() -> dict:
    """解析 .env 文件，返回配置字典"""
    # 从当前文件位置找到项目根目录的 .env（在 src/ 的上一级）
    current_dir = Path(__file__).parent.parent  # 从 src/config.py -> 项目根目录
    env_path = current_dir / ".env"

    config = {}

    if not env_path.exists():
        print(f"⚠️  .env 文件不存在: {env_path}")
        return config

    with open(env_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue

            # 解析 KEY=VALUE 格式
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # 去除引号
                if len(value) >= 2:
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                config[key] = value

    print(f"✅ 从 .env 加载了 {len(config)} 个配置项")
    return config


class Settings(BaseModel):
    """应用配置 - 直接从 .env 文件读取，不使用环境变量"""

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


# 加载 .env 文件
env_config = parse_env_file()

# 创建配置实例
settings = Settings(
    ENABLE_AI_POSTPROCESS=env_config.get("ENABLE_AI_POSTPROCESS", "false").lower() == "true",
    AI_PROVIDER=env_config.get("AI_PROVIDER", "openai"),
    OPENAI_API_KEY=env_config.get("OPENAI_API_KEY"),
    OPENAI_BASE_URL=env_config.get("OPENAI_BASE_URL"),
    OPENAI_MODEL=env_config.get("OPENAI_MODEL", "gpt-4o-mini"),
    GEMINI_API_KEY=env_config.get("GEMINI_API_KEY"),
    GEMINI_MODEL=env_config.get("GEMINI_MODEL", "gemini-3-flash-preview"),
    OLLAMA_BASE_URL=env_config.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    OLLAMA_MODEL=env_config.get("OLLAMA_MODEL", "qwen2.5:7b"),
)

# 打印配置（用于调试）
import logging
logger = logging.getLogger(__name__)
logger.info(f"配置加载完成: ENABLE_AI_POSTPROCESS={settings.ENABLE_AI_POSTPROCESS}, OPENAI_MODEL={settings.OPENAI_MODEL}")



def get_settings() -> Settings:
    """获取配置实例"""
    return settings
