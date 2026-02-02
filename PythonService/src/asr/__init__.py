"""
ASR Model Factory
Centralized model selection and instantiation
"""

import logging
from typing import Literal

logger = logging.getLogger(__name__)

# Model type selection
# Change this to switch between models
MODEL_TYPE: Literal["whisper", "vibevoice"] = "whisper"


def get_asr_model():
    """
    Get ASR model instance based on MODEL_TYPE

    This is the ONLY place you need to change to switch models.

    To switch to VibeVoice:
        1. Set MODEL_TYPE = "whisper" above
        2. Install dependency: uv add mlx-audio
        3. Restart backend

    Returns:
        ASR model instance (WhisperASR or VibeVoiceASR)
    """
    if MODEL_TYPE == "vibevoice":
        try:
            from .vibevoice_model import VibeVoiceASR
            logger.info("📦 Using VibeVoice ASR model")
            return VibeVoiceASR()
        except ImportError as e:
            logger.error(f"❌ Failed to import VibeVoice: {e}")
            logger.error("Falling back to Whisper...")
            logger.error("To use VibeVoice: uv add mlx-audio")
            # Fall back to Whisper
            from .whisper_model import WhisperASR
            return WhisperASR(model_size="large-v3")
    else:
        # Default: Whisper
        from .whisper_model import WhisperASR
        logger.info("📦 Using Whisper ASR model")
        return WhisperASR(model_size="large-v3")


def set_model_type(model_type: Literal["whisper", "vibevoice"]):
    """
    Set the model type globally

    Args:
        model_type: "whisper" or "vibevoice"
    """
    global MODEL_TYPE
    MODEL_TYPE = model_type
    logger.info(f"Model type set to: {model_type}")
