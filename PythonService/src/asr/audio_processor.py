"""
Audio Processing Utilities
Handle audio file loading, conversion, and preprocessing
"""

import io
import numpy as np
from typing import Tuple, Optional
from pydub import AudioSegment
from pydub.utils import make_chunks

from asr.model import AudioConfig


class AudioProcessor:
    """
    Audio file processing utilities

    Supports:
    - Loading audio files (WAV, MP3, M4A, etc.)
    - Converting to required format (16kHz/16bit mono)
    - Chunking audio for streaming
    - VAD preprocessing (future)
    """

    def __init__(self, config: Optional[AudioConfig] = None):
        """
        Initialize audio processor

        Args:
            config: Audio configuration
        """
        self.config = config or AudioConfig()

    def load_audio_file(
        self,
        file_path: Optional[str] = None,
        file_data: Optional[bytes] = None,
        file_format: Optional[str] = None
    ) -> AudioSegment:
        """
        Load audio file from path or bytes

        Args:
            file_path: Path to audio file
            file_data: Audio file data as bytes
            file_format: Format of audio data (required if file_data provided)

        Returns:
            AudioSegment object
        """
        if file_data:
            # Load from bytes
            if not file_format:
                raise ValueError("file_format must be provided when loading from bytes")
            audio = AudioSegment.from_file(io.BytesIO(file_data), format=file_format)
        elif file_path:
            # Load from file path
            audio = AudioSegment.from_file(file_path)
        else:
            raise ValueError("Either file_path or file_data must be provided")

        return audio

    def convert_to_asr_format(
        self,
        audio: AudioSegment
    ) -> Tuple[np.ndarray, dict]:
        """
        Convert audio to ASR model format

        Args:
            audio: Input audio segment

        Returns:
            Tuple of (audio_array, metadata)
        """
        # Convert to mono if stereo
        if audio.channels > 1:
            audio = audio.set_channels(1)

        # Resample to target sample rate if needed
        if audio.frame_rate != self.config.sample_rate:
            audio = audio.set_frame_rate(self.config.sample_rate)

        # Convert to 16-bit PCM
        audio = audio.sample_set_width(2)  # 2 bytes = 16-bit

        # Convert to numpy array
        samples = np.array(audio.get_array_of_samples())

        # Normalize to [-1, 1] for processing
        normalized = samples.astype(np.float32) / 32768.0

        # Metadata
        metadata = {
            "sample_rate": audio.frame_rate,
            "channels": audio.channels,
            "bit_depth": audio.sample_width * 8,
            "duration": len(audio) / 1000.0,  # milliseconds to seconds
            "frames": len(audio)
        }

        return normalized, metadata

    def chunk_audio(
        self,
        audio: np.ndarray,
        chunk_duration_ms: int = 1000
    ) -> list[np.ndarray]:
        """
        Split audio into chunks for streaming

        Args:
            audio: Audio data as numpy array
            chunk_duration_ms: Chunk duration in milliseconds

        Returns:
            List of audio chunks
        """
        # Calculate chunk size in samples
        chunk_size = int(self.config.sample_rate * (chunk_duration_ms / 1000.0))

        chunks = []
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i + chunk_size]
            if len(chunk) > 0:  # Only add non-empty chunks
                chunks.append(chunk)

        return chunks

    def process_audio_file(
        self,
        file_path: Optional[str] = None,
        file_data: Optional[bytes] = None,
        file_format: Optional[str] = None
    ) -> Tuple[np.ndarray, dict]:
        """
        Complete pipeline: load and convert audio file

        Args:
            file_path: Path to audio file
            file_data: Audio file data as bytes
            file_format: Format of audio data

        Returns:
            Tuple of (normalized_audio_array, metadata)
        """
        # Load audio
        audio = self.load_audio_file(file_path, file_data, file_format)

        # Convert to ASR format
        normalized, metadata = self.convert_to_asr_format(audio)

        return normalized, metadata

    def detect_silence(
        self,
        audio: np.ndarray,
        threshold: float = 0.01,
        min_silence_duration_ms: int = 500
    ) -> list[Tuple[int, int]]:
        """
        Detect silence regions in audio (basic VAD)

        Args:
            audio: Audio data
            threshold: Amplitude threshold for silence
            min_silence_duration_ms: Minimum silence duration in ms

        Returns:
            List of (start_sample, end_sample) tuples for silence regions
        """
        # Calculate amplitude envelope
        envelope = np.abs(audio)

        # Find regions below threshold
        below_threshold = envelope < threshold

        # Find runs of below_threshold
        silence_regions = []
        in_silence = False
        start = 0

        min_silence_samples = int(
            self.config.sample_rate * (min_silence_duration_ms / 1000.0)
        )

        for i, is_silent in enumerate(below_threshold):
            if is_silent and not in_silence:
                # Start of silence
                in_silence = True
                start = i
            elif not is_silent and in_silence:
                # End of silence
                in_silence = False
                if i - start >= min_silence_samples:
                    silence_regions.append((start, i))

        # Handle case where audio ends in silence
        if in_silence and len(audio) - start >= min_silence_samples:
            silence_regions.append((start, len(audio)))

        return silence_regions

    def remove_silence(
        self,
        audio: np.ndarray,
        threshold: float = 0.01,
        min_silence_duration_ms: int = 500
    ) -> np.ndarray:
        """
        Remove silence regions from audio

        Args:
            audio: Audio data
            threshold: Amplitude threshold
            min_silence_duration_ms: Minimum duration

        Returns:
            Audio with silence removed
        """
        silence_regions = self.detect_silence(
            audio, threshold, min_silence_duration_ms
        )

        if not silence_regions:
            return audio

        # Keep non-silent regions
        result_segments = []
        prev_end = 0

        for start, end in silence_regions:
            # Keep audio before silence
            if start > prev_end:
                result_segments.append(audio[prev_end:start])
            prev_end = end

        # Keep audio after last silence
        if prev_end < len(audio):
            result_segments.append(audio[prev_end:])

        if result_segments:
            return np.concatenate(result_segments)
        else:
            return audio

    def normalize_volume(
        self,
        audio: np.ndarray,
        target_dBFS: float = -20.0
    ) -> np.ndarray:
        """
        Normalize audio to target volume level

        Args:
            audio: Audio data
            target_dBFS: Target volume in dBFS

        Returns:
            Normalized audio
        """
        # Calculate current RMS
        rms = np.sqrt(np.mean(audio ** 2))

        # Avoid division by zero
        if rms < 1e-9:
            return audio

        # Calculate desired RMS
        desired_rms = 10 ** (target_dBFS / 20.0)

        # Calculate gain
        gain = desired_rms / rms

        # Limit gain to avoid excessive amplification
        gain = min(gain, 10.0)

        return audio * gain
