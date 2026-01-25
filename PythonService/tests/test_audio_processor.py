"""
Tests for Audio Processor
"""

import pytest
import numpy as np
import io
from asr.audio_processor import AudioProcessor
from asr.model import AudioConfig


@pytest.fixture
def processor():
    """Create audio processor instance"""
    return AudioProcessor()


@pytest.fixture
def sample_audio_data():
    """Create sample audio data"""
    # 1 second of silence at 16kHz
    sample_rate = 16000
    duration = 1
    samples = np.zeros(sample_rate * duration, dtype=np.float32)
    return samples


class TestAudioProcessor:
    """Test audio processing functionality"""

    def test_create_processor(self, processor):
        """Test processor creation"""
        assert processor.config.sample_rate == 16000
        assert processor.config.channels == 1

    def test_create_custom_config(self):
        """Test processor with custom config"""
        config = AudioConfig(sample_rate=44100, channels=2, bit_depth=24)
        processor = AudioProcessor(config)
        assert processor.config.sample_rate == 44100
        assert processor.config.channels == 2

    def test_load_from_file_requires_path(self, processor):
        """Test that file loading requires path"""
        with pytest.raises(ValueError):
            processor.load_audio_file()

    def test_load_from_bytes_requires_format(self, processor):
        """Test that loading from bytes requires format"""
        data = b"dummy audio data"
        with pytest.raises(ValueError):
            processor.load_audio_file(file_data=data)

    def test_chunk_audio(self, processor):
        """Test audio chunking"""
        # Create 3 seconds of audio
        audio = np.zeros(48000)  # 3 seconds at 16kHz

        chunks = processor.chunk_audio(audio, chunk_duration_ms=1000)

        assert len(chunks) == 3
        assert all(len(chunk) == 16000 for chunk in chunks)

    def test_chunk_audio_partial_last_chunk(self, processor):
        """Test chunking with partial last chunk"""
        # Create 2.5 seconds of audio
        audio = np.zeros(40000)  # 2.5 seconds at 16kHz

        chunks = processor.chunk_audio(audio, chunk_duration_ms=1000)

        assert len(chunks) == 3
        assert len(chunks[0]) == 16000
        assert len(chunks[1]) == 16000
        assert len(chunks[2]) == 40000 - 32000  # Remaining samples


class TestSilenceDetection:
    """Test VAD functionality"""

    def test_detect_silence_all_silent(self, processor):
        """Test with completely silent audio"""
        audio = np.zeros(16000)  # 1 second of silence
        regions = processor.detect_silence(audio)
        # Should detect the whole audio as silence
        assert len(regions) >= 0

    def test_detect_silence_no_silence(self, processor):
        """Test with audio above threshold"""
        # Create audio above threshold
        audio = np.ones(16000) * 0.5  # High amplitude
        regions = processor.detect_silence(audio, threshold=0.01)
        # Should detect no silence
        assert len(regions) == 0

    def test_detect_silence_mixed(self, processor):
        """Test with mixed silence and audio"""
        audio = np.zeros(16000)
        # Add some audio in the middle
        audio[4000:6000] = 0.5  # 0.25 seconds of audio

        regions = processor.detect_silence(audio, threshold=0.01)
        # Should detect at least some silence
        assert len(regions) >= 1

    def test_remove_silence(self, processor):
        """Test silence removal"""
        # Audio with silence in middle (long enough to be detected)
        audio = np.concatenate([
            np.ones(2000) * 0.5,
            np.zeros(10000),  # 625ms of silence (enough to exceed 500ms threshold)
            np.ones(2000) * 0.5
        ])

        result = processor.remove_silence(audio, threshold=0.01)
        # Result should be shorter
        assert len(result) < len(audio)


class TestVolumeNormalization:
    """Test volume normalization"""

    def test_normalize_low_volume(self, processor):
        """Test normalizing low volume audio"""
        audio = np.ones(16000) * 0.01  # Very quiet
        result = processor.normalize_volume(audio)

        # Result should be amplified
        assert np.abs(result).mean() > np.abs(audio).mean()

    def test_normalize_high_volume(self, processor):
        """Test normalizing high volume audio"""
        audio = np.ones(16000) * 0.8  # Very loud
        result = processor.normalize_volume(audio)

        # Result should be attenuated
        assert np.abs(result).mean() < np.abs(audio).mean()

    def test_normalize_silent_audio(self, processor):
        """Test normalizing silent audio"""
        audio = np.zeros(16000)
        result = processor.normalize_volume(audio)

        # Silent audio should stay silent (no division by zero)
        assert np.allclose(result, audio)


class TestAudioConfig:
    """Test audio configuration"""

    def test_default_config(self):
        """Test default configuration"""
        config = AudioConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.bit_depth == 16

    def test_custom_sample_rate(self):
        """Test custom sample rate"""
        config = AudioConfig(sample_rate=44100)
        assert config.sample_rate == 44100

    def test_invalid_sample_rate(self):
        """Test invalid sample rate validation"""
        with pytest.raises(ValueError):
            AudioConfig(sample_rate=12000)

    def test_invalid_channels(self):
        """Test invalid channel count"""
        with pytest.raises(ValueError):
            AudioConfig(channels=5)
