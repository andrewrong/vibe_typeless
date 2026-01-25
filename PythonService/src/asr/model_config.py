"""
ASR Model Configuration Management
Manages model selection and configuration for ASR models
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class ModelSize(str, Enum):
    """Available model sizes for Whisper"""
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

    @classmethod
    def all(cls) -> List[str]:
        """Get all available model sizes"""
        return [m.value for m in cls]

    def description(self) -> str:
        """Get model description"""
        descriptions = {
            "tiny": "Tiny (39M) - Fastest, good for quick tests",
            "base": "Base (74M) - Balanced speed and accuracy",
            "small": "Small (244M) - Better accuracy, still fast",
            "medium": "Medium (769M) - High accuracy, slower",
            "large": "Large (1.5B) - Best accuracy, slowest"
        }
        return descriptions.get(self.value, "Unknown")


@dataclass
class ASRModelConfig:
    """ASR Model Configuration"""
    model_size: str = ModelSize.BASE.value
    language: Optional[str] = None  # None = auto-detect
    fp16: bool = True  # Use fp16 for memory efficiency

    def __post_init__(self):
        # Validate model size
        if self.model_size not in ModelSize.all():
            raise ValueError(
                f"Invalid model_size: {self.model_size}. "
                f"Must be one of {ModelSize.all()}"
            )


@dataclass
class ModelInfo:
    """Information about a model"""
    size: str
    params: str
    download_size: str
    ram_required: str
    speed: str
    description: str

    @classmethod
    def get_all(cls) -> dict[str, 'ModelInfo']:
        """Get info for all available models"""
        return {
            "tiny": ModelInfo(
                size="tiny",
                params="39M",
                download_size="~40MB",
                ram_required="1GB",
                speed="⚡⚡⚡ Fastest",
                description="Fastest, good for quick tests"
            ),
            "base": ModelInfo(
                size="base",
                params="74M",
                download_size="~150MB",
                ram_required="1GB",
                speed="⚡⚡ Very Fast",
                description="Balanced speed and accuracy"
            ),
            "small": ModelInfo(
                size="small",
                params="244M",
                download_size="~500MB",
                ram_required="2GB",
                speed="⚡ Fast",
                description="Better accuracy, still fast"
            ),
            "medium": ModelInfo(
                size="medium",
                params="769M",
                download_size="~1.5GB",
                ram_required="5GB",
                speed="🐢 Moderate",
                description="High accuracy, slower"
            ),
            "large": ModelInfo(
                size="large",
                params="1.5B",
                download_size="~3GB",
                ram_required="10GB",
                speed="🐌 Slow",
                description="Best accuracy, slowest"
            )
        }


class ModelManager:
    """
    Manages ASR model configuration and lifecycle
    """

    def __init__(self):
        self._config = ASRModelConfig()
        self._model_instance = None

    @property
    def config(self) -> ASRModelConfig:
        """Get current configuration"""
        return self._config

    @property
    def current_model_size(self) -> str:
        """Get current model size"""
        return self._config.model_size

    def set_model_size(self, model_size: str) -> None:
        """
        Change model size

        Args:
            model_size: New model size (tiny/base/small/medium/large)

        Raises:
            ValueError: If model_size is invalid
        """
        # Validate
        if model_size not in ModelSize.all():
            raise ValueError(
                f"Invalid model_size: {model_size}. "
                f"Must be one of {ModelSize.all()}"
            )

        # Update config
        old_model = self._config.model_size
        self._config.model_size = model_size

        # Reset model instance (will be reloaded on next use)
        self._model_instance = None

        print(f"Model switched from '{old_model}' to '{model_size}'")

    def set_language(self, language: Optional[str]) -> None:
        """
        Set language for transcription

        Args:
            language: Language code (e.g., 'en', 'zh', 'ja')
                     None for auto-detect
        """
        self._config.language = language
        self._model_instance = None

    def set_fp16(self, fp16: bool) -> None:
        """
        Set fp16 mode

        Args:
            fp16: Whether to use fp16 quantization
        """
        self._config.fp16 = fp16
        self._model_instance = None

    def get_available_models(self) -> dict[str, ModelInfo]:
        """Get information about all available models"""
        return ModelInfo.get_all()

    def get_model_info(self, model_size: str) -> ModelInfo:
        """
        Get information about a specific model

        Args:
            model_size: Model size to query

        Returns:
            ModelInfo object

        Raises:
            ValueError: If model_size is invalid
        """
        models = self.get_available_models()
        if model_size not in models:
            raise ValueError(f"Unknown model: {model_size}")
        return models[model_size]

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self._config = ASRModelConfig()
        self._model_instance = None


# Global model manager instance
model_manager = ModelManager()
