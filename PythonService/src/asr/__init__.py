"""
ASR Model Factory
Centralized model selection and instantiation

Supported models:
- whisper: MLX Whisper (default, requires mlx-whisper)
- vibevoice: MLX VibeVoice (requires mlx-audio)
- sensevoice: sherpa-onnx SenseVoice (requires sherpa-onnx)
"""

import logging
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# Model type selection
# Change this to switch between models
MODEL_TYPE: Literal["whisper", "vibevoice", "sensevoice"] = "sensevoice"

# Global singleton model instances per language (prevents memory leaks from repeated model loading)
_cached_models: dict = {}
_default_language: str = "zh"


def get_asr_model(language: str = "auto"):
    """
    Get ASR model instance based on MODEL_TYPE (SINGLETON PATTERN per language)

    This caches the model instances per language to prevent memory leaks.
    For SenseVoice, each language has its own recognizer instance.

    To switch models:
        1. Set MODEL_TYPE = "sensevoice" (or other) below
        2. Install the appropriate dependency:
           - whisper: uv add mlx-whisper (default)
           - vibevoice: uv add mlx-audio
           - sensevoice: uv add sherpa-onnx
        3. Reset model cache: reset_model_cache()
        4. Restart backend

    Model Comparison:
        Model        | Size    | Speed      | Accuracy | Language Support
        ------------|----------|------------|----------|------------------
        SenseVoice    | 228MB   | ~70ms/10s  | >95%     | zh/en/ja/ko/yue
        Whisper-Large | 3GB     | 1-2s       | ~95%      | Multilingual
        VibeVoice     | TBD      | Fast       | TBD       | Multilingual

    Args:
        language: Language code ("auto", "zh", "en", "ja", "ko", "yue").
                Only used for SenseVoice. Defaults to "auto".

    Returns:
        ASR model instance
    """
    global _cached_models, _default_language

    # Use default language if not specified
    if language == "auto":
        language = _default_language

    # Create cache key based on model type and language
    cache_key = f"{MODEL_TYPE}_{language}"

    # Return cached instance if available
    if cache_key in _cached_models:
        logger.debug(f"Using cached model: {cache_key}")
        return _cached_models[cache_key]

    # Create new instance and cache it
    if MODEL_TYPE == "sensevoice":
        try:
            from .sensevoice_model import SenseVoiceASR
            logger.info(f"📦 Using SenseVoice ASR model (language={language}, 228MB)")
            _cached_models[cache_key] = SenseVoiceASR(use_int8=True, language=language)
        except ImportError as e:
            logger.error(f"❌ Failed to import SenseVoice: {e}")
            logger.error("To use SenseVoice: uv add sherpa-onnx")
            logger.error("Falling back to Whisper...")
            from .whisper_model import WhisperASR
            _cached_models[cache_key] = WhisperASR(model_size="large-v3")
    elif MODEL_TYPE == "vibevoice":
        try:
            from .vibevoice_model import VibeVoiceASR
            logger.info("📦 Using VibeVoice ASR model (singleton)")
            _cached_models[cache_key] = VibeVoiceASR()
        except ImportError as e:
            logger.error(f"❌ Failed to import VibeVoice: {e}")
            logger.error("To use VibeVoice: uv add mlx-audio")
            logger.error("Falling back to Whisper...")
            from .whisper_model import WhisperASR
            _cached_models[cache_key] = WhisperASR(model_size="large-v3")
    else:
        # Default: Whisper
        from .whisper_model import WhisperASR
        logger.info("📦 Using Whisper ASR model (singleton)")
        _cached_models[cache_key] = WhisperASR(model_size="large-v3")

    return _cached_models[cache_key]


def reset_model_cache():
    """
    Reset cached model instances.

    Use this when you need to switch model sizes or reload model.
    The next get_asr_model() call will create a new instance.

    WARNING: This will cause the old models to remain in memory until
    Python's GC runs. For production, prefer restarting the service.
    """
    global _cached_models
    logger.info("🔄 Resetting model cache")
    _cached_models = {}


def set_model_type(model_type: Literal["whisper", "vibevoice", "sensevoice"]):
    """
    Set model type globally

    This will reset the cache on next get_asr_model() call.

    Args:
        model_type: "whisper", "vibevoice", or "sensevoice"
    """
    global MODEL_TYPE, _cached_models

    if MODEL_TYPE != model_type:
        logger.info(f"Switching model from {MODEL_TYPE} to {model_type}")
        MODEL_TYPE = model_type
        _cached_models = {}  # Reset cache
    else:
        logger.debug(f"Model type already set to: {model_type}")


def get_model_info() -> dict:
    """
    Get information about the current model

    Returns:
        Dict with model info
    """
    first_cached = next(iter(_cached_models.values()), None) if _cached_models else None
    return {
        "type": MODEL_TYPE,
        "cached_languages": list(_cached_models.keys()),
        "sample_rate": first_cached.sample_rate if first_cached else 16000,
    }


__all__ = ["get_asr_model", "reset_model_cache", "set_model_type", "get_model_info", "MODEL_TYPE"]
