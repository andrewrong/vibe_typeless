"""
Audio Processing Pipeline
Implements VoiceInk-style audio processing chain
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """A speech segment with timestamps"""
    audio: np.ndarray
    start_sample: int
    end_sample: int
    is_speech: bool


class SileroVAD:
    """
    Silero Voice Activity Detection
    Detects speech vs silence in audio
    """

    def __init__(self, threshold: float = 0.5):
        """
        Initialize VAD

        Args:
            threshold: Speech threshold (0.0-1.0), higher = more strict
        """
        self.threshold = threshold
        self.model = None

    def load_model(self):
        """Load Silero VAD model"""
        try:
            # Use silero-vad from torch hub
            import torch
            torch.hub.set_dir(self._get_cache_dir())

            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )

            self.model = model
            logger.info("Silero VAD loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}")
            return False

    def _get_cache_dir(self) -> str:
        """Get cache directory for models"""
        import os
        # Get project root (PythonService directory)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))

        # Use runtime/models/vad for VAD models
        cache_dir = os.path.join(project_root, "runtime", "models", "vad")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def process(self, audio: np.ndarray, sample_rate: int = 16000) -> List[AudioSegment]:
        """
        Process audio and detect speech segments

        Args:
            audio: Audio samples (int16 or float32)
            sample_rate: Sample rate (default 16000)

        Returns:
            List of AudioSegment with speech/silence labels
        """
        if self.model is None:
            if not self.load_model():
                logger.warning("VAD not available, returning full audio as speech")
                return [AudioSegment(audio, 0, len(audio), is_speech=True)]

        import torch

        # Convert to float32 if needed
        if audio.dtype == np.int16:
            audio_float = audio.astype(np.float32) / 32768.0
        else:
            audio_float = audio.astype(np.float32)

        # Process in chunks (same as Silero default window)
        window_size_samples = 512  # 32ms at 16kHz
        segments = []

        for i in range(0, len(audio_float), window_size_samples):
            chunk = audio_float[i:i + window_size_samples]

            # Pad if too short
            if len(chunk) < window_size_samples:
                chunk = np.pad(chunk, (0, window_size_samples - len(chunk)))

            # Convert to torch tensor
            tensor_chunk = torch.from_numpy(chunk).unsqueeze(0)

            # Get speech probability
            with torch.no_grad():
                prob = self.model(tensor_chunk, sample_rate).item()

            is_speech = prob >= self.threshold

            segments.append(AudioSegment(
                audio=audio[i:i + window_size_samples],
                start_sample=i,
                end_sample=min(i + window_size_samples, len(audio)),
                is_speech=is_speech
            ))

        return segments

    def merge_speech_segments(self, segments: List[AudioSegment],
                              min_speech_duration: float = 0.3,
                              min_silence_duration: float = 0.3) -> List[AudioSegment]:
        """
        Merge short speech segments and fill gaps

        Args:
            segments: VAD output segments
            min_speech_duration: Minimum speech duration (seconds)
            min_silence_duration: Maximum silence to keep (seconds)

        Returns:
            Merged speech segments
        """
        if not segments:
            return []

        sample_rate = 16000  # Assume 16kHz
        min_speech_samples = int(min_speech_duration * sample_rate)
        min_silence_samples = int(min_silence_duration * sample_rate)

        merged = []
        current_speech = []

        for seg in segments:
            if seg.is_speech:
                current_speech.append(seg)
            else:
                # Check if silence is short enough to bridge
                silence_duration = seg.end_sample - seg.start_sample

                if current_speech and silence_duration <= min_silence_samples:
                    # Keep the silence (bridge)
                    current_speech.append(seg)
                else:
                    # End current speech segment
                    if current_speech:
                        merged_audio = np.concatenate([s.audio for s in current_speech])
                        merged.append(AudioSegment(
                            audio=merged_audio,
                            start_sample=current_speech[0].start_sample,
                            end_sample=current_speech[-1].end_sample,
                            is_speech=True
                        ))
                        current_speech = []

        # Don't forget the last segment
        if current_speech:
            merged_audio = np.concatenate([s.audio for s in current_speech])
            merged.append(AudioSegment(
                audio=merged_audio,
                start_sample=current_speech[0].start_sample,
                end_sample=current_speech[-1].end_sample,
                is_speech=True
            ))

        # Filter out very short speech segments
        filtered = [
            seg for seg in merged
            if len(seg.audio) >= min_speech_samples
        ]

        return filtered


class AudioEnhancer:
    """
    Audio enhancement pipeline
    - Noise reduction
    - Normalization
    - DC offset removal
    """

    def __init__(self):
        """Initialize audio enhancer"""
        pass

    def normalize(self, audio: np.ndarray, target_rms: float = 0.1) -> np.ndarray:
        """
        RMS normalize audio

        Args:
            audio: Input audio
            target_rms: Target RMS level

        Returns:
            Normalized audio
        """
        if len(audio) == 0:
            return audio

        # Convert to float
        if audio.dtype == np.int16:
            audio_float = audio.astype(np.float32) / 32768.0
        else:
            audio_float = audio.astype(np.float32)

        # Calculate RMS
        rms = np.sqrt(np.mean(audio_float ** 2))

        if rms > 0:
            gain = target_rms / rms
            normalized = audio_float * gain
        else:
            normalized = audio_float

        # Clip to prevent distortion
        normalized = np.clip(normalized, -1.0, 1.0)

        return normalized

    def remove_dc_offset(self, audio: np.ndarray) -> np.ndarray:
        """
        Remove DC offset from audio

        Args:
            audio: Input audio

        Returns:
            Audio with DC offset removed
        """
        if len(audio) == 0:
            return audio

        # Convert to float if needed
        if audio.dtype == np.int16:
            audio_float = audio.astype(np.float32) / 32768.0
        else:
            audio_float = audio.astype(np.float32)

        # Remove mean (DC offset)
        dc_removed = audio_float - np.mean(audio_float)

        return dc_removed

    def bandpass_filter(self, audio: np.ndarray,
                       lowcut: float = 300.0,
                       highcut: float = 3400.0,
                       sample_rate: int = 16000) -> np.ndarray:
        """
        Apply bandpass filter for speech frequencies

        Args:
            audio: Input audio
            lowcut: Low frequency cutoff (Hz)
            highcut: High frequency cutoff (Hz)
            sample_rate: Sample rate

        Returns:
            Filtered audio
        """
        from scipy import signal

        # Design Butterworth bandpass filter
        nyquist = sample_rate / 2
        low = lowcut / nyquist
        high = highcut / nyquist

        b, a = signal.butter(4, [low, high], btype='band')

        # Apply filter
        filtered = signal.filtfilt(b, a, audio)

        return filtered

    def enhance(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply full enhancement pipeline

        Args:
            audio: Input audio

        Returns:
            Enhanced audio
        """
        # Step 1: Remove DC offset
        enhanced = self.remove_dc_offset(audio)

        # Step 2: Normalize
        enhanced = self.normalize(enhanced)

        # Step 3: Bandpass filter (optional, requires scipy)
        try:
            enhanced = self.bandpass_filter(enhanced)
        except ImportError:
            logger.warning("scipy not available, skipping bandpass filter")

        return enhanced


class AudioPipeline:
    """
    Complete audio processing pipeline
    VAD → Enhancement → Segmentation → Ready for ASR
    """

    def __init__(self,
                 vad_threshold: float = 0.5,
                 enable_enhancement: bool = True,
                 enable_vad: bool = True):
        """
        Initialize audio pipeline

        Args:
            vad_threshold: VAD threshold (0.0-1.0)
            enable_enhancement: Enable audio enhancement
            enable_vad: Enable VAD
        """
        self.vad = SileroVAD(threshold=vad_threshold) if enable_vad else None
        self.enhancer = AudioEnhancer() if enable_enhancement else None
        self.enable_vad = enable_vad
        self.enable_enhancement = enable_enhancement

        logger.info(f"AudioPipeline initialized: VAD={enable_vad}, Enhancement={enable_enhancement}")

    def process(self, audio: np.ndarray) -> Tuple[List[np.ndarray], dict]:
        """
        Process audio through complete pipeline

        Args:
            audio: Input audio (int16)

        Returns:
            Tuple of (processed_segments, stats)
        """
        stats = {
            "original_samples": len(audio),
            "original_duration": len(audio) / 16000.0,
            "segments": 0,
            "speech_samples": 0,
            "silence_removed": 0
        }

        processed_audio = audio.astype(np.float32) / 32768.0

        # Step 1: Audio enhancement
        if self.enhancer:
            logger.info("🔧 Applying audio enhancement...")
            processed_audio = self.enhancer.enhance(processed_audio)

        # Step 2: VAD to remove silence
        segments_list = [processed_audio]

        if self.vad:
            logger.info("🎤 Running VAD...")
            vad_segments = self.vad.process(processed_audio)

            # Merge speech segments
            speech_segments = self.vad.merge_speech_segments(
                vad_segments,
                min_speech_duration=0.3,
                min_silence_duration=0.3
            )

            if speech_segments:
                segments_list = [seg.audio for seg in speech_segments]
                stats["segments"] = len(speech_segments)
                stats["speech_samples"] = sum(len(seg) for seg in segments_list)
                stats["silence_removed"] = len(processed_audio) - stats["speech_samples"]

                logger.info(f"   VAD: {stats['segments']} speech segments, "
                          f"{stats['silence_removed'] / 16000:.2f}s silence removed")
            else:
                logger.warning("   No speech detected, using full audio")

        # Step 3: Convert back to int16 for Whisper
        segments_int16 = [
            (seg * 32767).astype(np.int16)
            for seg in segments_list
        ]

        return segments_int16, stats
