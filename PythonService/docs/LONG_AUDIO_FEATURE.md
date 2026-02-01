# Long Audio Processing Feature

## Overview

The long audio processing feature allows handling audio files longer than 30 seconds (Whisper's context limit) by intelligently chunking the audio into segments, transcribing each segment, and merging the results.

## Implementation

### Files Created/Modified

1. **src/asr/long_audio.py** (NEW)
   - `LongAudioProcessor` class with three chunking strategies
   - `AudioSegment` and `TranscriptionSegment` dataclasses
   - `process_long_audio()` convenience function
   - `LongAudioConfig` configuration model

2. **src/api/routes.py** (MODIFIED)
   - Added `/api/postprocess/upload-long` endpoint
   - Added `LongAudioProcessRequest` and `LongAudioProcessResponse` models
   - Fixed import: added `List` to typing imports

3. **tests/test_long_audio.py** (NEW)
   - 17 comprehensive tests covering all functionality
   - Tests for dataclasses, processor methods, API endpoint

4. **demo_long_audio.py** (NEW)
   - Interactive demonstration script
   - Shows different chunking strategies
   - Performance comparisons

## Chunking Strategies

### 1. Fixed-Length Chunking

Splits audio into fixed-duration chunks (default: 30 seconds) with overlap.

```python
processor = LongAudioProcessor(
    chunk_duration=30.0,  # seconds
    overlap=2.0           # seconds between chunks
)
segments = processor.split_fixed_chunks(audio)
```

**Best for:**
- Continuous speech without long pauses
- Predictable timing requirements
- Simple implementations

### 2. VAD-Based Chunking

Uses Voice Activity Detection to identify speech segments based on silence thresholds.

```python
processor = LongAudioProcessor(
    min_silence_duration=0.5,  # minimum silence for split
    silence_threshold=0.01     # audio level below which is silence
)
segments = processor.split_vad_chunks(audio)
```

**Best for:**
- Conversations with natural pauses
- Interviews and dialogues
- Recordings with variable speech patterns

### 3. Hybrid Chunking (Recommended)

Combines VAD for speech detection with fixed-length chunks for long speech sections.

```python
segments = processor.split_hybrid(
    audio,
    max_chunk_duration=60.0  # maximum duration for any chunk
)
```

**Best for:**
- Long recordings (> 1 minute)
- Mixed content (speech + silence)
- Meeting minutes, podcasts, lectures

## API Usage

### Endpoint: POST /api/postprocess/upload-long

**Request Parameters:**
- `file`: Audio file (WAV, MP3, M4A, FLAC, OGG, AAC)
- `strategy`: "fixed", "vad", or "hybrid" (default: "hybrid")
- `merge_strategy`: "simple", "overlap", or "smart" (default: "simple")
- `apply_postprocess`: true/false (default: true)

**Python Example:**
```python
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=300)

with open("long_audio.wav", "rb") as f:
    response = client.post(
        "/api/postprocess/upload-long",
        files={"file": f},
        params={
            "strategy": "hybrid",
            "merge_strategy": "simple",
            "apply_postprocess": "true"
        }
    )

result = response.json()
print(f"Transcript: {result['transcript']}")
print(f"Segments: {result['processing_stats']['num_segments']}")
```

**cURL Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/postprocess/upload-long \
  -F "file=@long_audio.wav" \
  -F "strategy=hybrid" \
  -F "merge_strategy=simple" \
  -F "apply_postprocess=true"
```

**Response:**
```json
{
  "transcript": "Full transcription text...",
  "processed_transcript": "Cleaned text with fillers removed...",
  "audio_metadata": {
    "duration": 120.5,
    "sample_rate": 16000,
    "channels": 1
  },
  "processing_stats": {
    "num_segments": 4,
    "strategy": "hybrid",
    "merge_strategy": "simple"
  },
  "segments": [
    {"segment_index": 0, "duration": 30.0},
    {"segment_index": 1, "duration": 30.0},
    {"segment_index": 2, "duration": 30.0},
    {"segment_index": 3, "duration": 30.5}
  ]
}
```

## Configuration

### LongAudioProcessor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sample_rate` | int | 16000 | Audio sample rate in Hz |
| `chunk_duration` | float | 30.0 | Target chunk duration in seconds |
| `overlap` | float | 2.0 | Overlap between chunks in seconds |
| `min_silence_duration` | float | 0.5 | Minimum silence to consider a split point |
| `silence_threshold` | float | 0.01 | Audio level below which is considered silence |

## Performance Considerations

### Processing Time

The processing time depends on:
1. **Audio duration**: Longer audio takes more time
2. **Number of segments**: More segments = more transcription calls
3. **Model size**: Larger models (base, small, medium) are slower
4. **Hardware**: Apple Silicon (M1/M2/M3) with MLX is much faster

**Expected Real-Time Factor (RTF)** on Apple Silicon:
- Tiny model: 0.04x (25x faster than real-time)
- Base model: 0.1x (10x faster than real-time)
- Small model: 0.3x (3x faster than real-time)

For example, processing 60 seconds of audio with the base model would take approximately 6 seconds.

### Memory Usage

Each audio segment is kept in memory during processing. For very long files (> 10 minutes), consider:
- Using VAD strategy to reduce number of segments
- Processing in batches
- Increasing chunk_duration to reduce segment count

## Merge Strategies

### Simple (Default)

Concatenates all transcripts with spaces between them.

```python
result = processor.merge_transcripts(transcripts, merge_strategy="simple")
```

### Overlap (Future Enhancement)

Handles overlapping regions between chunks to avoid duplication.

Currently implemented as simple concatenation. Future enhancement will:
- Detect overlapping text
- Merge overlapping regions intelligently
- Remove duplicate content

### Smart (Future Enhancement)

Advanced merging with punctuation and context awareness.

Planned features:
- Punctuation-aware merging
- Contextual analysis
- Better handling of sentence boundaries

## Limitations

1. **Whisper Context Limit**: Individual chunks are limited to 30 seconds
2. **Processing Time**: Long audio files can take significant time to process
3. **Memory Usage**: Very long files (> 10 minutes) may use considerable memory
4. **Overlap Handling**: Current implementation doesn't intelligently merge overlapping regions

## Future Enhancements

1. **Overlap Merging**
   - Detect overlapping text in adjacent chunks
   - Merge overlapping regions intelligently
   - Remove duplicate content

2. **Smart Segmentation**
   - Detect sentence boundaries
   - Split at logical pause points
   - Maintain context across segments

3. **Parallel Processing**
   - Process multiple segments concurrently
   - Faster overall processing time
   - Better utilization of multiple cores

4. **Progress Callbacks**
   - Report progress during processing
   - Show which segment is being processed
   - Provide estimated completion time

5. **Batch Processing**
   - Process multiple audio files in sequence
   - Generate batch reports
   - Export results to various formats

## Testing

Run the test suite:

```bash
uv run pytest tests/test_long_audio.py -v
```

Run the demo:

```bash
uv run python demo_long_audio.py
```

## Troubleshooting

### Issue: Empty Transcript

**Possible causes:**
- Audio level too low (below silence threshold)
- Wrong file format or sample rate
- Audio file is corrupted

**Solutions:**
- Check audio file with media player
- Try different `silence_threshold` value
- Use fixed strategy instead of VAD
- Verify file format and sample rate

### Issue: Too Many Segments

**Possible causes:**
- VAD detecting speech in noise
- Low silence threshold
- Short chunk duration

**Solutions:**
- Increase `silence_threshold`
- Increase `chunk_duration`
- Use fixed strategy instead of VAD

### Issue: Processing Timeout

**Possible causes:**
- File is too long
- Model is too large for hardware
- Network timeout (if using remote server)

**Solutions:**
- Increase client timeout value
- Use smaller model (tiny or base)
- Process in smaller chunks
- Use faster hardware

## Summary

The long audio processing feature successfully handles audio files longer than Whisper's 30-second limit through intelligent chunking. Three strategies are available (fixed, VAD, hybrid) to suit different use cases, with proper API integration and comprehensive testing.

For most use cases, the **hybrid strategy** provides the best balance between accuracy and performance.
