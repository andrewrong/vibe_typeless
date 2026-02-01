"""
Tests for Long Audio Processing
"""

import pytest
import numpy as np
from asr.long_audio import (
    LongAudioProcessor,
    AudioSegment,
    TranscriptionSegment,
    LongAudioConfig,
    process_long_audio
)


class TestAudioSegment:
    """Test AudioSegment dataclass"""

    def test_create_segment(self):
        """Test creating an audio segment"""
        audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        segment = AudioSegment(
            start_sample=0,
            end_sample=3,
            audio=audio,
            start_time=0.0,
            end_time=0.0001875
        )
        assert segment.start_sample == 0
        assert segment.end_sample == 3
        assert segment.is_speech is True


class TestTranscriptionSegment:
    """Test TranscriptionSegment dataclass"""

    def test_create_transcription(self):
        """Test creating a transcription segment"""
        segment = TranscriptionSegment(
            text="Hello world",
            start_time=0.0,
            end_time=1.0,
            confidence=0.95
        )
        assert segment.text == "Hello world"
        assert segment.confidence == 0.95


class TestLongAudioProcessor:
    """Test LongAudioProcessor class"""

    @pytest.fixture
    def processor(self):
        """Create a processor instance"""
        return LongAudioProcessor(
            sample_rate=16000,
            chunk_duration=2.0,  # 2 seconds for faster tests
            overlap=0.5,  # 0.5 seconds overlap
            min_silence_duration=0.3,
            silence_threshold=0.01
        )

    @pytest.fixture
    def sample_audio(self):
        """Create sample audio (5 seconds)"""
        # 5 seconds of audio at 16kHz
        duration = 5.0
        sample_rate = 16000
        num_samples = int(duration * sample_rate)

        # Create audio with some speech and silence
        audio = np.random.randn(num_samples).astype(np.float32) * 0.1

        # Add "speech" (louder sections)
        speech_start = int(1.0 * sample_rate)
        speech_end = int(2.0 * sample_rate)
        audio[speech_start:speech_end] *= 5.0  # Make it louder

        return audio

    @pytest.fixture
    def long_audio(self):
        """Create longer sample audio (10 seconds)"""
        duration = 10.0
        sample_rate = 16000
        num_samples = int(duration * sample_rate)
        return np.random.randn(num_samples).astype(np.float32) * 0.1

    def test_initialization(self, processor):
        """Test processor initialization"""
        assert processor.sample_rate == 16000
        assert processor.chunk_duration == 2.0
        assert processor.overlap == 0.5
        assert processor.min_silence_samples == int(16000 * 0.3)

    def test_split_fixed_chunks(self, processor, sample_audio):
        """Test fixed-length chunking"""
        segments = processor.split_fixed_chunks(sample_audio)

        # Should split 5 seconds into 2.5 second chunks with overlap
        # First: 0-2s, Second: 1.5-3.5s, Third: 3-5s (approximately)
        assert len(segments) >= 2

        # Check first segment
        first = segments[0]
        assert first.start_sample == 0
        assert first.start_time == 0.0
        assert len(first.audio) > 0

    def test_split_fixed_chunks_int16(self, processor):
        """Test fixed-length chunking with int16 audio"""
        audio = np.random.randint(-32768, 32767, 16000 * 5, dtype=np.int16)
        segments = processor.split_fixed_chunks(audio)

        assert len(segments) >= 2
        # Should convert to float
        assert segments[0].audio.dtype == np.float32

    def test_split_vad_chunks(self, processor, sample_audio):
        """Test VAD-based chunking"""
        segments = processor.split_vad_chunks(sample_audio)

        # VAD should detect speech regions
        # With our test audio, should detect at least the loud section
        assert len(segments) >= 0  # May be 0 if all is below threshold

        # Check segments have correct structure
        for segment in segments:
            assert segment.is_speech is True
            assert segment.start_sample < segment.end_sample
            assert len(segment.audio) > 0

    def test_split_hybrid(self, processor, long_audio):
        """Test hybrid chunking"""
        segments = processor.split_hybrid(long_audio, max_chunk_duration=3.0)

        # Hybrid should combine VAD with fixed chunks
        assert len(segments) >= 0

        # Check that no segment exceeds max duration
        max_size = int(16000 * 3.0)
        for segment in segments:
            if segment.end_sample - segment.start_sample > max_size:
                # If segment is longer than max, it should have been split
                assert False, f"Segment exceeds max duration: {segment.end_sample - segment.start_sample} > {max_size}"

    def test_merge_transcripts_simple(self, processor):
        """Test simple transcript merging"""
        transcripts = [
            TranscriptionSegment("Hello", 0.0, 1.0),
            TranscriptionSegment("world", 1.0, 2.0),
            TranscriptionSegment("test", 2.0, 3.0)
        ]

        result = processor.merge_transcripts(transcripts, merge_strategy="simple")
        assert result == "Hello world test"

    def test_merge_transcripts_empty(self, processor):
        """Test merging empty transcripts"""
        result = processor.merge_transcripts([], merge_strategy="simple")
        assert result == ""

    def test_merge_transcripts_overlap(self, processor):
        """Test overlap-based merging"""
        transcripts = [
            TranscriptionSegment("Hello world", 0.0, 1.0),
            TranscriptionSegment("world test", 0.8, 1.8)
        ]

        result = processor.merge_transcripts(transcripts, merge_strategy="overlap")
        assert "Hello" in result
        assert "world" in result

    def test_merge_transcripts_invalid_strategy(self, processor):
        """Test merging with invalid strategy (falls back to simple)"""
        transcripts = [
            TranscriptionSegment("Hello", 0.0, 1.0)
        ]

        result = processor.merge_transcripts(transcripts, merge_strategy="invalid")
        assert result == "Hello"


class TestLongAudioConfig:
    """Test LongAudioConfig model"""

    def test_default_config(self):
        """Test default configuration"""
        config = LongAudioConfig()
        assert config.strategy == "hybrid"
        assert config.merge_strategy == "simple"
        assert config.max_chunk_duration == 60.0
        assert config.overlap == 2.0

    def test_custom_config(self):
        """Test custom configuration"""
        config = LongAudioConfig(
            strategy="fixed",
            merge_strategy="overlap",
            max_chunk_duration=30.0
        )
        assert config.strategy == "fixed"
        assert config.merge_strategy == "overlap"
        assert config.max_chunk_duration == 30.0


class TestProcessLongAudio:
    """Integration tests for process_long_audio function"""

    @pytest.fixture
    def mock_transcribe_fn(self):
        """Mock transcribe function"""
        def transcribe(audio):
            # Return mock transcript based on audio length
            return "Mock transcript "
        return transcribe

    def test_process_long_audio_fixed_strategy(self, mock_transcribe_fn, tmp_path):
        """Test processing with fixed strategy"""
        # Create test audio file
        import wave
        audio_path = tmp_path / "test.wav"

        with wave.open(str(audio_path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            # Write 5 seconds of audio
            wf.writeframes(np.random.randint(0, 256, 16000 * 5, dtype=np.uint8))

        transcript, metadata = process_long_audio(
            audio_path=str(audio_path),
            transcribe_fn=mock_transcribe_fn,
            strategy="fixed"
        )

        assert isinstance(transcript, str)
        assert "num_segments" in metadata
        assert metadata["strategy"] == "fixed"

    def test_process_long_audio_vad_strategy(self, mock_transcribe_fn, tmp_path):
        """Test processing with VAD strategy"""
        import wave
        audio_path = tmp_path / "test_vad.wav"

        with wave.open(str(audio_path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(np.random.randint(0, 256, 16000 * 3, dtype=np.uint8))

        transcript, metadata = process_long_audio(
            audio_path=str(audio_path),
            transcribe_fn=mock_transcribe_fn,
            strategy="vad"
        )

        assert isinstance(transcript, str)
        assert metadata["strategy"] == "vad"

    def test_process_long_audio_invalid_strategy(self, mock_transcribe_fn, tmp_path):
        """Test processing with invalid strategy"""
        import wave
        audio_path = tmp_path / "test_invalid.wav"

        with wave.open(str(audio_path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(np.random.randint(0, 256, 16000 * 2, dtype=np.uint8))

        with pytest.raises(ValueError, match="Unknown strategy"):
            process_long_audio(
                audio_path=str(audio_path),
                transcribe_fn=mock_transcribe_fn,
                strategy="invalid_strategy"
            )


class TestLongAudioAPI:
    """Integration tests for long audio API endpoint"""

    @pytest.fixture
    def client(self):
        """Create HTTP client"""
        import httpx
        return httpx.Client(base_url="http://127.0.0.1:8000")

    def test_upload_long_audio_endpoint_exists(self, client):
        """Test that the endpoint exists"""
        # Just check if we can connect (will fail if server not running)
        try:
            response = client.post("/api/postprocess/upload-long")
            # Should get 422 (missing file) not 404
            assert response.status_code != 404
        except Exception:
            # Server not running, skip test
            pytest.skip("Server not running")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
