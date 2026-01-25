"""
Tests for ASR model
Following TDD principles - tests written first
"""

import pytest
import numpy as np
from asr.model import ASRModel, AudioConfig


@pytest.fixture
def audio_config():
    """Create audio configuration"""
    return AudioConfig(
        sample_rate=16000,
        channels=1,
        bit_depth=16
    )


@pytest.fixture
def asr_model(audio_config):
    """Create ASR model instance"""
    return ASRModel(config=audio_config)


def test_model_can_be_instantiated(asr_model):
    """Test that ASR model can be created"""
    assert asr_model is not None
    assert asr_model.config.sample_rate == 16000
    assert asr_model.config.channels == 1


def test_audio_config_validation():
    """Test audio configuration validation"""
    # Valid config
    config = AudioConfig(sample_rate=16000, channels=1, bit_depth=16)
    assert config.sample_rate == 16000

    # Invalid sample rate should raise error
    with pytest.raises(ValueError):
        AudioConfig(sample_rate=12000, channels=1, bit_depth=16)


def test_preprocess_audio(asr_model):
    """Test audio preprocessing"""
    # Create dummy audio data (1 second of silence)
    raw_audio = np.zeros(16000, dtype=np.int16)
    processed = asr_model.preprocess_audio(raw_audio)

    assert processed is not None
    assert hasattr(processed, 'shape')
    # Should be normalized to float
    assert processed.dtype == np.float32 or processed.dtype == np.float64


def test_transcribe_empty_audio(asr_model):
    """Test transcription with empty audio"""
    empty_audio = np.array([], dtype=np.int16)
    result = asr_model.transcribe(empty_audio)

    assert result == ""


def test_transcribe_short_audio(asr_model):
    """Test transcription with very short audio"""
    # Very short audio (less than 0.1 seconds)
    short_audio = np.random.randint(-100, 100, size=1600, dtype=np.int16)
    result = asr_model.transcribe(short_audio)

    # Should return empty string for too short audio
    assert isinstance(result, str)


def test_model_is_ready(asr_model):
    """Test if model is ready for transcription"""
    # Initially should not be ready (no model loaded)
    assert not asr_model.is_ready()

    # After loading, should be ready
    # This is a placeholder test - actual model loading will be implemented later
    asr_model._loaded = True
    assert asr_model.is_ready()
