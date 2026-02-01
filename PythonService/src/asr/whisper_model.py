"""
MLX Whisper implementation
Real ASR model using MLX Whisper with Apple Silicon optimization
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np
import tempfile


@dataclass
class AudioConfig:
    """Audio configuration for Whisper"""
    sample_rate: int = 16000
    channels: int = 1
    bit_depth: int = 16
    chunk_size_ms: int = 1000

    def __post_init__(self):
        # Whisper supports 16kHz sample rate
        if self.sample_rate != 16000:
            raise ValueError(f"Whisper requires 16kHz sample rate, got {self.sample_rate}")

        if self.channels not in [1, 2]:
            raise ValueError(f"Channels must be 1 or 2, got {self.channels}")

        if self.bit_depth not in [16, 24, 32]:
            raise ValueError(f"Bit depth must be 16, 24, or 32, got {self.bit_depth}")


class WhisperASR:
    """
    MLX Whisper ASR implementation

    Features:
    - Multi-language support (99+ languages)
    - 4-bit quantization available
    - Apple Silicon optimized
    - Multiple model sizes (tiny, base, small, medium, large)
    """

    # Available model sizes
    MODEL_SIZES = ["tiny", "base", "small", "medium", "large", "large-v3"]

    def __init__(
        self,
        config: Optional[AudioConfig] = None,
        model_size: str = "base"
    ):
        """
        Initialize Whisper ASR model

        Args:
            config: Audio configuration (uses default if None)
            model_size: Model size (tiny, base, small, medium, large, large-v3)
        """
        # Map large-v3 to large for compatibility
        original_model_size = model_size
        if model_size == "large-v3":
            model_size = "large"

        # Check if model_size is valid (use self.MODEL_SIZES)
        valid_sizes = ["tiny", "base", "small", "medium", "large"]
        if model_size not in valid_sizes:
            raise ValueError(
                f"model_size must be one of {valid_sizes}, got {model_size}"
            )

        self.config = config or AudioConfig()
        self.model_size = model_size
        self._original_model_size = original_model_size  # Store original
        self._model_loaded = False

    def load_model(self):
        """
        Load the Whisper model

        Note: MLX Whisper uses lazy loading, so this is a no-op.
        The model will be loaded on first transcription.
        """
        # MLX Whisper handles lazy loading internally
        self._model_loaded = True

    def preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Preprocess audio data

        Args:
            audio: Audio data as numpy array

        Returns:
            Preprocessed audio data
        """
        # Convert int16 to float32 if needed
        if audio.dtype == np.int16:
            normalized = audio.astype(np.float32) / 32768.0
        else:
            normalized = audio.astype(np.float32)

        # Ensure mono
        if len(normalized.shape) > 1 and normalized.shape[1] > 1:
            normalized = np.mean(normalized, axis=1)

        return normalized

    def transcribe_file(self, file_path: str, language: str = "zh") -> str:
        """
        Transcribe audio file

        Args:
            file_path: Path to audio file
            language: Language code (default: "zh" for Chinese)

        Returns:
            Transcribed text
        """
        try:
            import mlx_whisper

            # Map model size to MLX community model ID
            # MLX Whisper models are hosted at mlx-community on HuggingFace
            model_id = f"mlx-community/whisper-{self.model_size}-mlx"

            result = mlx_whisper.transcribe(
                file_path,
                path_or_hf_repo=model_id,
                fp16=True,  # Use float16 for efficiency
                language=language,  # Specify language for better accuracy
                temperature=0.0,  # Use 0 for more deterministic output
                compression_ratio_threshold=2.4,  # Filter out failures
                no_speech_threshold=0.6,  # Filter out silence
                condition_on_previous_text=False,  # Don't condition on previous text for fresh transcription
            )

            return result.get("text", "").strip()

        except ImportError:
            raise ImportError(
                "mlx-whisper is not installed. "
                "Run: uv pip install mlx-whisper"
            )
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}") from e

    def transcribe(self, audio: np.ndarray, language: str = "zh") -> str:
        """
        Transcribe audio array

        Args:
            audio: Audio data as numpy array (int16 or float32)
            language: Language code (default: "zh" for Chinese)

        Returns:
            Transcribed text
        """
        import logging
        logger = logging.getLogger(__name__)

        # Validate audio
        if len(audio) == 0:
            logger.warning("Empty audio array")
            return ""

        # Check minimum audio length (at least 0.1 seconds)
        min_samples = int(self.config.sample_rate * 0.1)
        if len(audio) < min_samples:
            logger.warning(f"Audio too short: {len(audio)} samples < {min_samples}")
            return ""

        logger.info(f"Transcribing {len(audio)} samples, dtype={audio.dtype}, range=[{audio.min()}, {audio.max()}]")

        # Save to temporary file
        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            mode="wb",
            delete=False
        ) as f:
            temp_path = f.name

        try:
            # Convert audio to correct format
            preprocessed = self.preprocess_audio(audio)
            logger.info(f"Preprocessed: shape={preprocessed.shape}, dtype={preprocessed.dtype}, range=[{preprocessed.min()}, {preprocessed.max()}]")

            # Convert back to int16 for WAV file
            audio_int16 = (preprocessed * 32767).astype(np.int16)
            logger.info(f"Int16: shape={audio_int16.shape}, dtype={audio_int16.dtype}, range=[{audio_int16.min()}, {audio_int16.max()}]")

            # Write WAV file manually
            import wave
            import struct

            with wave.open(temp_path, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.config.sample_rate)

                # Write audio data
                wav_file.writeframes(audio_int16.tobytes())

            logger.info(f"WAV file written to {temp_path}")

            # Transcribe with language specified
            result = self.transcribe_file(temp_path, language=language)
            logger.info(f"Transcription result: '{result}'")
            return result

        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            raise RuntimeError(f"Transcription failed: {e}") from e

        finally:
            # Cleanup temp file
            try:
                Path(temp_path).unlink()
            except:
                pass

    def transcribe_stream(self, audio_chunks: list[np.ndarray], language: str = "zh") -> str:
        """
        Transcribe streaming audio chunks

        Args:
            audio_chunks: List of audio chunks
            language: Language code (default: "zh" for Chinese)

        Returns:
            Combined transcription
        """
        # Handle empty chunks
        if not audio_chunks:
            return ""

        # Combine chunks
        combined_audio = np.concatenate(audio_chunks)

        # Transcribe combined audio with language
        return self.transcribe(combined_audio, language=language)

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._model_loaded
