"""
VibeVoice ASR implementation (Alternative approach)
Directly calls generate_transcription with preprocessed audio
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np
import tempfile
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Audio configuration for VibeVoice"""
    sample_rate: int = 16000
    channels: int = 1
    bit_depth: int = 16
    chunk_size_ms: int = 1000


class VibeVoiceASR:
    """
    VibeVoice ASR implementation with Whisper-compatible interface

    This version directly preprocesses audio and passes it to generate_transcription
    """

    MODEL_ID = "mlx-community/VibeVoice-ASR-8bit"

    def __init__(
        self,
        config: Optional[AudioConfig] = None,
        model_id: str = None
    ):
        self.config = config or AudioConfig()
        self.model_id = model_id or self.MODEL_ID
        self._loaded = False

        logger.info(f"VibeVoiceASR initialized with model: {self.model_id}")

    def _resample_to_24khz(self, audio: np.ndarray) -> np.ndarray:
        """Resample audio from 16kHz to 24kHz"""
        try:
            import scipy.signal as signal
        except ImportError:
            logger.error("scipy is required for audio resampling")
            raise ImportError("Install scipy: uv add scipy")

        target_sr = 24000
        original_sr = 16000
        number_of_samples = round(len(audio) * float(target_sr) / original_sr)
        resampled_audio = signal.resample_poly(audio, number_of_samples, len(audio))

        # Convert back to int16
        if resampled_audio.dtype != np.int16:
            resampled_audio = (resampled_audio * 32767).astype(np.int16)

        return resampled_audio

    def transcribe(
        self,
        audio: np.ndarray,
        language: str = "auto"
    ) -> str:
        """
        Transcribe audio to text

        Args:
            audio: Audio data as int16 numpy array (16kHz, mono)
            language: Language code ("zh", "en", "auto", etc.)

        Returns:
            Transcribed text
        """
        if len(audio) == 0:
            logger.warning("Empty audio array provided")
            return ""

        # Resample to 24kHz
        audio_24khz = self._resample_to_24khz(audio)
        logger.debug(f"Resampled audio: {len(audio)} -> {len(audio_24khz)} samples")

        # Save to temporary WAV file at 24kHz
        import wave
        fd, wav_path = tempfile.mkstemp(suffix="_24khz.wav")

        try:
            with wave.open(wav_path, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(24000)
                wav_file.writeframes(audio_24khz.tobytes())

            logger.debug(f"Saved 24kHz audio to {wav_path}")

            # Import and call generate_transcription
            from mlx_audio.stt.generate import generate_transcription

            logger.debug(f"Transcribing {len(audio_24khz)} samples ({len(audio_24khz)/24000:.2f}s)...")

            # Pass as a numpy array instead of file path to avoid load_audio issues
            # Actually, let's try with file path first but use a simpler approach
            try:
                # Try with just the file path
                result = generate_transcription(
                    model=self.model_id,
                    audio_path=wav_path,
                    format="text",
                    verbose=False
                )
            except Exception as e:
                logger.error(f"generate_transcription failed: {e}")
                # Fallback: return empty string
                return ""

            # Extract text
            if hasattr(result, 'text'):
                text = result.text
            elif isinstance(result, str):
                text = result
            else:
                text = str(result)

            # Clean up result
            text = text.strip()

            logger.debug(f"Transcription result: '{text[:50]}...'")
            return text

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            import traceback
            traceback.print_exc()
            return ""
        finally:
            # Clean up temporary file
            try:
                import os
                os.close(fd)
                os.unlink(wav_path)
            except:
                pass
