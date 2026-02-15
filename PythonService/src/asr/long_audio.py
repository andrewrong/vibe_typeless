"""
Long Audio Processing Module
Handles audio files longer than 30 seconds by intelligent chunking
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from pydantic import BaseModel


@dataclass
class AudioSegment:
    """A segment of audio with metadata"""
    start_sample: int
    end_sample: int
    audio: np.ndarray
    start_time: float
    end_time: float
    is_speech: bool = True


@dataclass
class TranscriptionSegment:
    """A transcribed segment with timing info"""
    text: str
    start_time: float
    end_time: float
    confidence: float = 1.0


class LongAudioProcessor:
    """
    Process long audio files by intelligently chunking them

    Strategies:
    1. Fixed-length chunking with overlap
    2. VAD-based chunking (speech activity detection)
    3. Hybrid (VAD + fixed chunks for speech sections)
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration: float = 30.0,  # seconds
        overlap: float = 2.0,  # seconds
        min_silence_duration: float = 0.5,  # seconds
        silence_threshold: float = 0.01
    ):
        """
        Initialize long audio processor

        Args:
            sample_rate: Audio sample rate
            chunk_duration: Target chunk duration in seconds
            overlap: Overlap between chunks in seconds
            min_silence_duration: Minimum silence to consider a split point
            silence_threshold: Audio level below which is considered silence
        """
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.overlap = overlap
        self.min_silence_duration = min_silence_duration
        self.silence_threshold = silence_threshold

        # Calculate sizes in samples
        self.chunk_size = int(sample_rate * chunk_duration)
        self.overlap_size = int(sample_rate * overlap)
        self.min_silence_samples = int(sample_rate * min_silence_duration)

    def split_fixed_chunks(
        self,
        audio: np.ndarray
    ) -> List[AudioSegment]:
        """
        Split audio into fixed-length chunks with overlap

        Args:
            audio: Audio array (float or int16)

        Returns:
            List of AudioSegment objects
        """
        # Convert to float if needed
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0

        # Calculate total samples
        total_samples = len(audio)

        segments = []
        start_sample = 0

        while start_sample < total_samples:
            end_sample = min(start_sample + self.chunk_size, total_samples)

            segment = AudioSegment(
                start_sample=start_sample,
                end_sample=end_sample,
                audio=audio[start_sample:end_sample],
                start_time=start_sample / self.sample_rate,
                end_time=end_sample / self.sample_rate
            )

            segments.append(segment)

            # Move to next chunk (with overlap)
            start_sample = end_sample - self.overlap_size

        return segments

    def split_vad_chunks(
        self,
        audio: np.ndarray
    ) -> List[AudioSegment]:
        """
        Split audio using Voice Activity Detection

        Args:
            audio: Audio array (float or int16)

        Returns:
            List of AudioSegment objects
        """
        # Convert to float if needed
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0

        # Calculate envelope (absolute value)
        envelope = np.abs(audio)

        # Detect silence regions
        is_speech = envelope > self.silence_threshold

        # Find speech segments
        segments = []
        in_speech = False
        start_idx = 0

        for i, is_speech_frame in enumerate(is_speech):
            if is_speech_frame and not in_speech:
                # Start of speech segment
                start_idx = i
                in_speech = True
            elif not is_speech_frame and in_speech:
                # End of speech segment
                if (i - start_idx) >= self.min_silence_samples:
                    segment = AudioSegment(
                        start_sample=start_idx,
                        end_sample=i,
                        audio=audio[start_idx:i],
                        start_time=start_idx / self.sample_rate,
                        end_time=i / self.sample_rate,
                        is_speech=True
                    )
                    segments.append(segment)
                    in_speech = False

        # Handle case where audio ends with speech
        if in_speech:
            segment = AudioSegment(
                start_sample=start_idx,
                end_sample=len(audio),
                audio=audio[start_idx:],
                start_time=start_idx / self.sample_rate,
                end_time=len(audio) / self.sample_rate,
                is_speech=True
            )
            segments.append(segment)

        return segments

    def split_hybrid(
        self,
        audio: np.ndarray,
        max_chunk_duration: float = 60.0
    ) -> List[AudioSegment]:
        """
        Hybrid approach: VAD for speech detection,
        then split long speech sections into fixed chunks

        Args:
            audio: Audio array
            max_chunk_duration: Maximum duration for any chunk

        Returns:
            List of AudioSegment objects
        """
        # First, get VAD segments
        vad_segments = self.split_vad_chunks(audio)

        # Then, split long segments into fixed chunks
        final_segments = []
        max_size = int(self.sample_rate * max_chunk_duration)

        for segment in vad_segments:
            if segment.end_sample - segment.start_sample > max_size:
                # Split into smaller chunks
                start = segment.start_sample
                while start < segment.end_sample:
                    end = min(start + max_size, segment.end_sample)
                    final_segments.append(AudioSegment(
                        start_sample=start,
                        end_sample=end,
                        audio=segment.audio[start - segment.start_sample:end - segment.start_sample],
                        start_time=start / self.sample_rate,
                        end_time=end / self.sample_rate,
                        is_speech=True
                    ))
                    start = end
            else:
                final_segments.append(segment)

        return final_segments

    def merge_transcripts(
        self,
        transcripts: List[TranscriptionSegment],
        merge_strategy: str = "simple"
    ) -> str:
        """
        Merge transcript segments into final output

        Args:
            transcripts: List of transcribed segments
            merge_strategy: "simple", "overlap", or "smart"

        Returns:
            Merged transcript text
        """
        if not transcripts:
            return ""

        if merge_strategy == "simple":
            # Just concatenate
            return " ".join([t.text for t in transcripts])

        elif merge_strategy == "overlap":
            # Handle overlapping regions (future enhancement)
            return self._merge_with_overlap(transcripts)

        elif merge_strategy == "smart":
            # Smart merging with punctuation and timing (future)
            return self._merge_smart(transcripts)

        else:
            return self.merge_transcripts(transcripts, "simple")

    def _merge_with_overlap(
        self,
        transcripts: List[TranscriptionSegment]
    ) -> str:
        """
        Merge transcripts handling overlapping regions
        """
        if not transcripts:
            return ""

        # Sort by start time
        transcripts = sorted(transcripts, key=lambda x: x.start_time)

        # Simple concatenation for now
        # TODO: Implement proper overlap handling
        result = []
        prev_end = 0

        for t in transcripts:
            # Add separator if there's a gap
            if t.start_time > prev_end:
                result.append("...")

            result.append(t.text.strip())
            prev_end = t.end_time

        return " ".join(result)

    def _merge_smart(
        self,
        transcripts: List[TranscriptionSegment]
    ) -> str:
        """
        Smart merging with punctuation and context awareness
        """
        # For now, use simple concatenation
        # This can be enhanced later with:
        # - Overlap detection and merging
        # - Punctuation-aware merging
        # - Contextual analysis
        return self._merge_with_overlap(transcripts)


# Convenience functions

def process_long_audio(
    audio_path: str,
    transcribe_fn,
    strategy: str = "hybrid",
    merge_strategy: str = "simple"
) -> Tuple[str, Dict]:
    """
    Process long audio file

    Args:
        audio_path: Path to audio file
        transcribe_fn: Function that takes audio array and returns text
        strategy: "fixed", "vad", or "hybrid"
        merge_strategy: How to merge transcripts

    Returns:
        Tuple of (full_transcript, metadata)
    """
    from src.asr.audio_processor import AudioProcessor

    # Load audio
    processor = AudioProcessor()
    audio, metadata = processor.process_audio_file(file_path=audio_path)

    # Split into segments
    long_audio_processor = LongAudioProcessor()

    if strategy == "fixed":
        segments = long_audio_processor.split_fixed_chunks(audio)
    elif strategy == "vad":
        segments = long_audio_processor.split_vad_chunks(audio)
    elif strategy == "hybrid":
        segments = long_audio_processor.split_hybrid(audio)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    # Transcribe each segment
    transcripts = []
    total_duration = metadata.get("duration", 0)

    for i, segment in enumerate(segments):
        print(f"  Processing segment {i+1}/{len(segments)} "
              f"({segment.end_time - segment.start_time:.1f}s)...")

        # Convert audio to int16 for transcription
        audio_int16 = (segment.audio * 32767).astype(np.int16)

        # Transcribe
        text = transcribe_fn(audio_int16)
        print(f"    -> Transcript: '{text}'")

        transcripts.append(TranscriptionSegment(
            text=text,
            start_time=segment.start_time,
            end_time=segment.end_time
        ))

    # Merge transcripts
    full_transcript = long_audio_processor.merge_transcripts(
        transcripts,
        merge_strategy=merge_strategy
    )

    metadata.update({
        "num_segments": len(segments),
        "strategy": strategy,
        "merge_strategy": merge_strategy
    })

    return full_transcript, metadata


@dataclass
class LongAudioConfig(BaseModel):
    """Configuration for long audio processing"""
    strategy: str = "hybrid"  # fixed, vad, hybrid
    merge_strategy: str = "simple"  # simple, overlap, smart
    max_chunk_duration: float = 60.0  # seconds
    overlap: float = 2.0  # seconds
    min_silence_duration: float = 0.5  # seconds
    silence_threshold: float = 0.01
