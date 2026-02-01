"""
Optimized Whisper ASR with VAD and audio preprocessing
Improves transcription quality by:
1. Voice Activity Detection (VAD) to remove silence
2. Audio normalization
3. Optimized Whisper parameters
"""

import numpy as np
import wave
import struct
import logging
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass
import tempfile

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """Audio segment with VAD information"""
    audio: np.ndarray
    start: float
    end: float
    is_speech: bool


class VoiceActivityDetector:
    """
    Voice Activity Detection using WebRTC VAD
    Filters out non-speech segments to improve Whisper accuracy
    """

    def __init__(self, sample_rate: int = 16000, frame_duration: int = 30):
        """
        Initialize VAD

        Args:
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000)
            frame_duration: Frame duration in ms (10, 20, or 30)
        """
        import webrtcvad

        self.sample_rate = sample_rate
        self.frame_duration = frame_duration
        self.vad = webrtcvad.Vad(2)  # Aggressiveness level 0-3, 2 is balanced

    def detect_speech(self, audio: np.ndarray) -> List[AudioSegment]:
        """
        Detect speech segments in audio

        Args:
            audio: Audio data (int16 numpy array)

        Returns:
            List of AudioSegment objects
        """
        # Convert to int16 if needed
        if audio.dtype != np.int16:
            if audio.dtype == np.float32 or audio.dtype == np.float64:
                audio = (audio * 32767).astype(np.int16)
            else:
                audio = audio.astype(np.int16)

        # Calculate frame size
        frame_length = int(self.sample_rate * self.frame_duration / 1000)

        # Split into frames
        frames = []
        for i in range(0, len(audio), frame_length):
            frame = audio[i:i + frame_length]

            # Pad last frame if needed
            if len(frame) < frame_length:
                frame = np.pad(frame, (0, frame_length - len(frame)), constant_values=0)

            # Convert to bytes for VAD
            frame_bytes = frame.tobytes()

            # Check if speech
            is_speech = self.vad.is_speech(frame_bytes, self.sample_rate)

            start_time = i / self.sample_rate
            end_time = (i + len(frame)) / self.sample_rate

            frames.append(AudioSegment(
                audio=frame,
                start=start_time,
                end=end_time,
                is_speech=is_speech
            ))

        # Merge consecutive speech frames
        return self._merge_speech_segments(frames)

    def _merge_speech_segments(self, frames: List[AudioSegment]) -> List[AudioSegment]:
        """
        Merge consecutive speech frames into segments

        Args:
            frames: List of AudioSegment frames

        Returns:
            List of merged AudioSegment objects
        """
        if not frames:
            return []

        merged = []
        current_speech = []
        in_speech = False

        for frame in frames:
            if frame.is_speech:
                if not in_speech:
                    # Start new speech segment
                    in_speech = True
                    current_speech = [frame]
                else:
                    # Continue speech segment
                    current_speech.append(frame)
            else:
                if in_speech:
                    # End speech segment
                    if current_speech:
                        merged_audio = np.concatenate([f.audio for f in current_speech])
                        merged.append(AudioSegment(
                            audio=merged_audio,
                            start=current_speech[0].start,
                            end=current_speech[-1].end,
                            is_speech=True
                        ))
                    current_speech = []
                    in_speech = False

        # Handle last segment
        if current_speech:
            merged_audio = np.concatenate([f.audio for f in current_speech])
            merged.append(AudioSegment(
                audio=merged_audio,
                start=current_speech[0].start,
                end=current_speech[-1].end,
                is_speech=True
            ))

        return merged


class AudioPreprocessor:
    """
    Audio preprocessing for better Whisper transcription
    """

    @staticmethod
    def normalize_audio(audio: np.ndarray) -> np.ndarray:
        """
        Normalize audio to prevent clipping

        Args:
            audio: Audio data

        Returns:
            Normalized audio
        """
        if audio.dtype == np.int16:
            # Convert to float for processing
            audio = audio.astype(np.float32) / 32768.0

        # Normalize to [-1, 1]
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val

        return audio

    @staticmethod
    def remove_silence(audio: np.ndarray, sample_rate: int = 16000,
                       silence_threshold: float = 0.01, min_silence_duration: float = 0.5) -> np.ndarray:
        """
        Remove silence from audio using energy-based detection

        Args:
            audio: Audio data
            sample_rate: Sample rate
            silence_threshold: Energy threshold for silence
            min_silence_duration: Minimum duration to consider as silence (seconds)

        Returns:
            Audio with silence removed
        """
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0

        # Calculate energy
        frame_length = int(sample_rate * 0.025)  # 25ms frames
        energy = []
        for i in range(0, len(audio), frame_length):
            frame = audio[i:i + frame_length]
            if len(frame) == frame_length:
                energy.append(np.mean(frame ** 2))

        if not energy:
            return audio

        energy = np.array(energy)

        # Detect silence
        is_speech = energy > silence_threshold
        is_speech = AudioPreprocessor._smooth_speech_detection(
            is_speech,
            min_silence_frames=int(min_silence_duration * sample_rate / frame_length)
        )

        # Extract speech segments
        speech_segments = []
        in_speech = False
        start_idx = 0

        for i, speech in enumerate(is_speech):
            if speech and not in_speech:
                start_idx = i * frame_length
                in_speech = True
            elif not speech and in_speech:
                end_idx = min((i + 1) * frame_length, len(audio))
                speech_segments.append(audio[start_idx:end_idx])
                in_speech = False

        # Handle last segment
        if in_speech:
            speech_segments.append(audio[start_idx:])

        if speech_segments:
            return np.concatenate(speech_segments)
        return audio

    @staticmethod
    def _smooth_speech_detection(is_speech: np.ndarray, min_silence_frames: int) -> np.ndarray:
        """
        Smooth speech detection to avoid rapid switching

        Args:
            is_speech: Boolean array of speech detection
            min_silence_frames: Minimum frames to consider as silence

        Returns:
            Smoothed boolean array
        """
        smoothed = is_speech.copy()
        silence_count = 0

        for i in range(len(is_speech)):
            if not is_speech[i]:
                silence_count += 1
                if silence_count < min_silence_frames:
                    smoothed[i] = True
            else:
                silence_count = 0

        return smoothed


class OptimizedWhisperASR:
    """
    Optimized Whisper ASR with VAD and preprocessing
    """

    def __init__(self, model_size: str = "medium", use_vad: bool = True):
        """
        Initialize optimized Whisper ASR

        Args:
            model_size: Model size (tiny, base, small, medium, large)
            use_vad: Whether to use VAD
        """
        self.model_size = model_size
        self.use_vad = use_vad
        self.vad = VoiceActivityDetector() if use_vad else None
        self.preprocessor = AudioPreprocessor()

    def transcribe(self, audio: np.ndarray, language: str = "zh") -> str:
        """
        Transcribe audio with optimizations

        Args:
            audio: Audio data (int16 numpy array)
            language: Language code

        Returns:
            Transcribed text
        """
        if len(audio) == 0:
            logger.warning("Empty audio array")
            return ""

        logger.info(f"Transcribing {len(audio)} samples with VAD={self.use_vad}")

        audio_to_transcribe = audio

        # Try VAD if enabled
        if self.use_vad and self.vad is not None:
            try:
                # Preprocess audio
                audio_normalized = self.preprocessor.normalize_audio(audio)

                # Use VAD to get speech segments
                speech_segments = self.vad.detect_speech(audio_normalized)

                if speech_segments:
                    # Calculate total speech duration
                    total_speech_samples = sum(len(seg.audio) for seg in speech_segments)
                    speech_ratio = total_speech_samples / len(audio)

                    logger.info(f"VAD detected {len(speech_segments)} speech segments, {speech_ratio:.1%} of audio")

                    # Only use VAD result if speech ratio is reasonable (>10%)
                    if speech_ratio > 0.1:
                        # Combine all speech segments
                        speech_audio = np.concatenate([seg.audio for seg in speech_segments])

                        # Convert back to int16
                        if speech_audio.dtype == np.float32 or speech_audio.dtype == np.float64:
                            speech_audio = (speech_audio * 32767).astype(np.int16)

                        audio_to_transcribe = speech_audio
                    else:
                        logger.warning(f"Speech ratio too low ({speech_ratio:.1%}), using original audio")
                else:
                    logger.warning("No speech detected by VAD, using original audio")

            except Exception as e:
                logger.error(f"VAD processing failed: {e}, using original audio")
                # Fall back to original audio

        # Transcribe with optimized parameters
        return self._transcribe_with_params(audio_to_transcribe, language)

    def _transcribe_with_params(self, audio: np.ndarray, language: str) -> str:
        """
        Transcribe with optimized Whisper parameters

        Args:
            audio: Audio data (int16)
            language: Language code

        Returns:
            Transcribed text
        """
        try:
            import mlx_whisper

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", mode="wb", delete=False) as f:
                temp_path = f.name

            # Write WAV file
            with wave.open(temp_path, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(audio.tobytes())

            try:
                # Use optimized parameters for better accuracy
                model_id = f"mlx-community/whisper-{self.model_size}-mlx"

                result = mlx_whisper.transcribe(
                    temp_path,
                    path_or_hf_repo=model_id,
                    fp16=True,
                    language=language,
                    # Basic parameters that MLX Whisper supports
                    temperature=0.0,  # Lower temperature for deterministic output
                )

                transcript = result.get("text", "").strip()
                logger.info(f"Transcription result: '{transcript}'")
                return transcript

            finally:
                # Cleanup
                try:
                    Path(temp_path).unlink()
                except:
                    pass

        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            raise RuntimeError(f"Transcription failed: {e}") from e
