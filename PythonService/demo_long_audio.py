#!/usr/bin/env python3
"""
Demonstrate Long Audio Processing
Show how to process audio files longer than 30 seconds
"""

import httpx
import time
import os
import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine

BASE_URL = "http://127.0.0.1:8000"


def generate_test_audio(duration_seconds: int, filename: str) -> str:
    """
    Generate test audio file with specified duration

    Args:
        duration_seconds: Duration of audio in seconds
        filename: Output filename

    Returns:
        Path to generated audio file
    """
    print(f"Generating {duration_seconds}s test audio: {filename}...")

    # Generate audio with speech-like segments
    sample_rate = 16000

    # Create base audio with sine waves to simulate speech patterns
    audio = AudioSegment.silent(duration=duration_seconds * 1000)

    # Add "speech" segments (alternating tones)
    segment_duration = 2000  # 2 seconds
    for i in range(0, duration_seconds * 1000, segment_duration * 2):
        # Speech-like segment
        tone1 = Sine(440).to_audio_segment(duration=segment_duration // 2) - 10
        tone2 = Sine(880).to_audio_segment(duration=segment_duration // 2) - 10
        speech = tone1 + tone2

        # Overlay speech at different positions
        pos = min(i + segment_duration, len(audio) - len(speech))
        if pos >= 0:
            audio = audio.overlay(speech, position=pos)

    # Export as WAV
    audio.export(filename, format="wav", parameters=["-ar", "16000", "-ac", "1"])

    file_size = os.path.getsize(filename) / (1024 * 1024)
    print(f"  ✓ Generated {filename} ({file_size:.2f} MB)")

    return filename


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def demo_long_audio_strategies():
    """Demonstrate different long audio processing strategies"""

    print_section("🎙️  Long Audio Processing Demo")

    client = httpx.Client(base_url=BASE_URL, timeout=300)

    # Test durations (in seconds)
    test_durations = [35, 60, 120]

    strategies = ["fixed", "vad", "hybrid"]

    for duration in test_durations:
        print(f"\n{'=' * 70}")
        print(f"Testing with {duration}s audio file")
        print(f"{'=' * 70}")

        # Generate test audio
        filename = f"test_audio_{duration}s.wav"
        generate_test_audio(duration, filename)

        try:
            with open(filename, "rb") as f:
                audio_data = f.read()

            # Test each strategy
            for strategy in strategies:
                print(f"\n{strategy.upper()} Strategy:")
                print("-" * 70)

                files = {"file": (filename, audio_data, "audio/wav")}

                start = time.time()
                response = client.post(
                    f"/api/postprocess/upload-long?strategy={strategy}&merge_strategy=simple&apply_postprocess=true",
                    files=files
                )
                elapsed = time.time() - start

                if response.status_code == 200:
                    result = response.json()

                    print(f"✅ Processing complete ({elapsed:.2f}s)")
                    print(f"   Audio duration: {duration}s")
                    print(f"   Processing speed: {elapsed / duration:.2f}x RTF")
                    print(f"   Number of segments: {result['processing_stats']['num_segments']}")
                    print(f"   Strategy used: {result['processing_stats']['strategy']}")
                    print(f"   Merge strategy: {result['processing_stats']['merge_strategy']}")

                    if result['transcript']:
                        transcript_preview = result['transcript'][:100]
                        print(f"   Transcript preview: \"{transcript_preview}...\"")
                    else:
                        print("   ⚠️  No transcript generated (audio may be too quiet)")

                    if result.get('processed_transcript'):
                        print(f"   Post-processing applied")

                else:
                    print(f"❌ Error: {response.status_code}")
                    print(f"   {response.text}")

        except Exception as e:
            print(f"\n❌ Error processing {duration}s audio: {e}")

        finally:
            # Clean up
            if os.path.exists(filename):
                os.unlink(filename)
                print(f"\n  Cleaned up {filename}")

    # Summary
    print_section("Summary")

    print("""
💡 Long Audio Processing Strategies:

1️⃣  FIXED (Fixed-Length Chunking)
   • Splits audio into 30-second chunks with 2-second overlap
   • Simple and predictable
   • Best for: Continuous speech, predictable timing

2️⃣  VAD (Voice Activity Detection)
   • Detects speech segments automatically
   • Splits at silence boundaries
   • Best for: Conversations with pauses, interviews

3️⃣  HYBRID (Recommended)
   • Combines VAD + fixed-length chunking
   • Detects speech, then splits long sections into 30s chunks
   • Best for: Long recordings, mixed content

📊 When to use each strategy:

  Use Case                    | Strategy
  ----------------------------|----------
  Podcasts/Monologues         | HYBRID
  Interviews/Conversations    | VAD
  Continuous Recording        | FIXED
  Meeting Minutes             | HYBRID
  Voice Notes                 | VAD
  Dictation                   | HYBRID

🔧 Configuration:

  Strategy:     strategy=hybrid    # fixed, vad, hybrid
  Max chunk:    max_chunk_duration=60  # seconds
  Overlap:      overlap=2.0        # seconds between chunks
  Merge:        merge_strategy=simple  # simple, overlap, smart

📖 API Usage:

  # Python
  import httpx

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

  # cURL
  curl -X POST http://127.0.0.1:8000/api/postprocess/upload-long \\
    -F "file=@long_audio.wav" \\
    -F "strategy=hybrid" \\
    -F "merge_strategy=simple" \\
    -F "apply_postprocess=true"
    """)

    print("\n" + "=" * 70)
    print("✅ Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        demo_long_audio_strategies()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
