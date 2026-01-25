"""
Tests for MLX Whisper model
"""

import pytest
import numpy as np
from pathlib import Path

from asr.whisper_model import WhisperASR, AudioConfig


class TestAudioConfig:
    """Test AudioConfig validation"""

    def test_default_config(self):
        """Test default configuration"""
        config = AudioConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.bit_depth == 16
        assert config.chunk_size_ms == 1000

    def test_invalid_sample_rate(self):
        """Test invalid sample rate raises error"""
        with pytest.raises(ValueError):
            AudioConfig(sample_rate=24000, channels=1, bit_depth=16)

    def test_invalid_channels(self):
        """Test invalid channels raises error"""
        with pytest.raises(ValueError):
            AudioConfig(sample_rate=16000, channels=3, bit_depth=16)

    def test_invalid_bit_depth(self):
        """Test invalid bit depth raises error"""
        with pytest.raises(ValueError):
            AudioConfig(sample_rate=16000, channels=1, bit_depth=8)


class TestWhisperASR:
    """Test Whisper ASR model"""

    @pytest.fixture
    def model(self):
        """Create model instance"""
        config = AudioConfig()
        return WhisperASR(config=config, model_size="base")

    def test_model_initialization(self, model):
        """Test model initializes without loading"""
        assert model.config.sample_rate == 16000
        assert model.model_size == "base"
        assert not model.is_loaded

    def test_invalid_model_size(self):
        """Test invalid model size raises error"""
        config = AudioConfig()
        with pytest.raises(ValueError):
            WhisperASR(config=config, model_size="invalid")

    def test_valid_model_sizes(self):
        """Test all valid model sizes"""
        config = AudioConfig()
        for size in ["tiny", "base", "small", "medium", "large"]:
            model = WhisperASR(config=config, model_size=size)
            assert model.model_size == size

    def test_preprocess_audio_int16(self, model):
        """Test audio preprocessing from int16"""
        audio = np.array([1000, -1000, 0, 500, -500], dtype=np.int16)
        processed = model.preprocess_audio(audio)

        assert processed.dtype == np.float32
        assert len(processed) == len(audio)
        # Check normalization range (-1 to 1)
        assert np.all(processed >= -1.0) and np.all(processed <= 1.0)

    def test_preprocess_audio_float(self, model):
        """Test audio preprocessing from float"""
        audio = np.array([0.5, -0.5, 0.0, 0.3, -0.3], dtype=np.float32)
        processed = model.preprocess_audio(audio)

        assert processed.dtype == np.float32
        assert len(processed) == len(audio)

    def test_preprocess_stereo_to_mono(self, model):
        """Test stereo audio is converted to mono"""
        audio = np.array([[0.5, 0.3], [-0.5, -0.3], [0.0, 0.0]], dtype=np.float32)
        processed = model.preprocess_audio(audio)

        assert len(processed.shape) == 1  # Mono
        assert len(processed) == 3  # Same number of samples

    def test_load_model(self, model):
        """Test model loading"""
        model.load_model()
        assert model.is_loaded

    def test_transcribe_empty_audio(self, model):
        """Test transcribing empty audio returns empty string"""
        audio = np.array([], dtype=np.int16)
        result = model.transcribe(audio)
        assert result == ""

    def test_transcribe_short_audio(self, model):
        """Test transcribing very short audio returns empty string"""
        # Create audio less than 0.1 seconds (1600 samples at 16kHz)
        audio = np.random.randint(-1000, 1000, size=1000, dtype=np.int16)
        result = model.transcribe(audio)
        # Should return empty for very short audio
        assert result == ""

    def test_transcribe_with_noise(self, model):
        """Test transcribing audio with noise"""
        # Create 1 second of audio noise
        audio = np.random.randint(-1000, 1000, size=16000, dtype=np.int16)

        # This should not crash, may return empty or some text
        result = model.transcribe(audio)
        assert isinstance(result, str)

    def test_transcribe_stream_empty(self, model):
        """Test streaming transcription with empty chunks"""
        result = model.transcribe_stream([])
        assert result == ""

    def test_transcribe_stream_single_chunk(self, model):
        """Test streaming transcription with single chunk"""
        # Create 1 second of audio
        audio = np.random.randint(-1000, 1000, size=16000, dtype=np.int16)
        result = model.transcribe_stream([audio])
        assert isinstance(result, str)

    def test_transcribe_stream_multiple_chunks(self, model):
        """Test streaming transcription with multiple chunks"""
        # Create multiple audio chunks
        chunks = [
            np.random.randint(-1000, 1000, size=16000, dtype=np.int16)
            for _ in range(3)
        ]
        result = model.transcribe_stream(chunks)
        assert isinstance(result, str)


class TestWhisperASRIntegration:
    """Integration tests for Whisper ASR"""

    @pytest.fixture
    def model(self):
        """Create and load model"""
        config = AudioConfig()
        model = WhisperASR(config=config, model_size="tiny")  # Use tiny for faster testing
        model.load_model()
        return model

    def test_model_has_correct_size(self, model):
        """Test model uses correct model size"""
        assert model.model_size == "tiny"

    def test_model_sizes_constant(self):
        """Test MODEL_SIZES constant"""
        expected = ["tiny", "base", "small", "medium", "large"]
        assert WhisperASR.MODEL_SIZES == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
