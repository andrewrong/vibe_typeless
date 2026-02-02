"""
VibeVoice ASR implementation
Alternative to Whisper using VibeVoice model with MLX
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

    def __post_init__(self):
        # VibeVoice supports 16kHz sample rate
        if self.sample_rate != 16000:
            raise ValueError(f"VibeVoice requires 16kHz sample rate, got {self.sample_rate}")

        if self.channels not in [1, 2]:
            raise ValueError(f"Channels must be 1 or 2, got {self.channels}")

        if self.bit_depth not in [16, 24, 32]:
            raise ValueError(f"Bit depth must be 16, 24, or 32, got {self.bit_depth}")


class VibeVoiceASR:
    """
    VibeVoice ASR implementation with Whisper-compatible interface

    Features:
    - 9B parameter speech-to-text model
    - 8-bit quantization
    - Apple Silicon optimized via MLX
    - Speaker diarization support
    - Multi-language support

    Usage:
        model = VibeVoiceASR()
        text = model.transcribe(audio_array, language="zh")
    """

    MODEL_ID = "mlx-community/VibeVoice-ASR-8bit"

    def __init__(
        self,
        config: Optional[AudioConfig] = None,
        model_id: str = None
    ):
        """
        Initialize VibeVoice ASR model

        Args:
            config: Audio configuration (uses default if None)
            model_id: Model ID (default: mlx-community/VibeVoice-ASR-8bit)
        """
        self.config = config or AudioConfig()
        self.model_id = model_id or self.MODEL_ID
        self._model = None
        self._loaded = False

        logger.info(f"VibeVoiceASR initialized with model: {self.model_id}")

    def _load_model(self):
        """Lazy load the model"""
        if self._loaded:
            return

        # VibeVoice doesn't need explicit model loading
        # generate_transcription will handle it
        self._loaded = True
        logger.info(f"✅ VibeVoice ready (model will be loaded on first use)")

    def _save_audio_to_wav(self, audio: np.ndarray) -> str:
        """
        Save numpy array to temporary WAV file

        Args:
            audio: Audio data as int16 numpy array

        Returns:
            Path to temporary WAV file
        """
        import wave

        # Validate input
        if audio.dtype != np.int16:
            logger.warning(f"Audio dtype is {audio.dtype}, converting to int16")
            audio = (audio * 32767).astype(np.int16) if audio.dtype == np.float32 else audio.astype(np.int16)

        # Create temporary file
        fd, wav_path = tempfile.mkstemp(suffix=".wav")

        try:
            # Write WAV file
            with wave.open(wav_path, 'wb') as wav_file:
                wav_file.setnchannels(self.config.channels)
                wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                wav_file.setframerate(self.config.sample_rate)
                wav_file.writeframes(audio.tobytes())

            logger.debug(f"Saved audio to {wav_path}: {len(audio)} samples")
            return wav_path
        except Exception as e:
            # Clean up fd if wav writing fails
            import os
            os.close(fd)
            raise e

    def _preprocess_audio_for_vibevoice(self, audio: np.ndarray) -> str:
        """
        Preprocess audio for VibeVoice (needs 24kHz)

        Args:
            audio: Audio data as int16 numpy array (16kHz)

        Returns:
            Path to resampled WAV file (24kHz)
        """
        import wave
        import scipy.signal as signal

        # Validate input
        if audio.dtype != np.int16:
            audio = (audio * 32767).astype(np.int16) if audio.dtype == np.float32 else audio.astype(np.int16)

        # Normalize to [-1, 1] before resampling
        audio_normalized = audio.astype(np.float32) / 32768.0

        # Resample from 16kHz to 24kHz
        target_sr = 24000
        original_sr = 16000
        number_of_samples = round(len(audio_normalized) * float(target_sr) / original_sr)
        resampled_audio = signal.resample_poly(audio_normalized, number_of_samples, len(audio_normalized))

        # Clip to [-1, 1] to prevent overflow
        resampled_audio = np.clip(resampled_audio, -1.0, 1.0)

        # Convert back to int16
        resampled_audio = (resampled_audio * 32767).astype(np.int16)

        # Create temporary file
        fd, wav_path = tempfile.mkstemp(suffix="_24khz.wav")

        try:
            # Write WAV file at 24kHz
            with wave.open(wav_path, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(target_sr)
                wav_file.writeframes(resampled_audio.tobytes())

            logger.debug(f"Saved 24kHz audio to {wav_path}: {len(resampled_audio)} samples")
            return wav_path
        except Exception as e:
            import os
            os.close(fd)
            raise e

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

        # Resample to 24kHz and save
        wav_path = self._preprocess_audio_for_vibevoice(audio)
        logger.debug(f"Saved 24kHz audio to {wav_path}")

        try:
            # Use our own load_audio that doesn't use mx.array
            from mlx_audio.audio_io import read as audio_read
            import mlx.core as mx

            # Read audio at 24kHz
            audio_data, sr = audio_read(wav_path, always_2d=True)
            logger.debug(f"Loaded audio: shape={audio_data.shape}, sr={sr}")

            # Convert to mx array (float32)
            audio_tensor = mx.array(audio_data, dtype=mx.float32).mean(axis=1)
            logger.debug(f"Created mx array: shape={audio_tensor.shape}")

            # Now load model and transcribe
            from mlx_audio.stt.utils import load_model

            model = load_model(self.model_id)
            logger.debug(f"Model loaded: {type(model)}")

            # Call model.generate directly with audio tensor
            logger.debug(f"Generating transcription...")

            # Generate expects audio in specific format
            result = model.generate(
                audio=audio_tensor,
                **{}  # Additional kwargs if needed
            )

            # Extract text from result
            # VibeVoice returns STTOutput object with .text and .segments attributes
            logger.debug(f"Result type: {type(result)}")

            if hasattr(result, 'text'):
                # STTOutput has .text attribute (contains JSON)
                json_text = result.text
                logger.debug(f"Result.text: {json_text[:100]}")

                # Parse JSON to extract content
                try:
                    import json
                    segments = json.loads(json_text)
                    if isinstance(segments, list):
                        # Extract content from each segment
                        text_parts = [seg.get('Content', '') for seg in segments if seg.get('Content')]
                        text = ' '.join(text_parts)
                        logger.debug(f"Extracted text: {text}")
                    else:
                        text = json_text
                except Exception as e:
                    logger.debug(f"JSON parsing failed: {e}, using raw text")
                    text = json_text
            elif isinstance(result, str):
                text = result
            elif isinstance(result, list) and len(result) > 0:
                text = ' '.join([str(seg) for seg in result])
            else:
                text = str(result)

            text = text.strip()
            logger.debug(f"Final transcription: '{text[:50]}...'")
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
                os.unlink(wav_path)
            except:
                pass

    def transcribe_with_timestamps(
        self,
        audio: np.ndarray,
        language: str = "auto"
    ) -> list[dict]:
        """
        Transcribe audio with timestamps (if supported)

        Args:
            audio: Audio data as int16 numpy array
            language: Language code

        Returns:
            List of segments with start, end, and text
        """
        # For now, just return a single segment
        # VibeVoice may support speaker diarization in the future
        text = self.transcribe(audio, language)
        return [{
            "start": 0.0,
            "end": len(audio) / 16000,
            "text": text
        }]
