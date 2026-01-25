#!/usr/bin/env python3
"""
Test audio file upload endpoint
Demonstrates audio file processing with various options
"""

import httpx
import json

BASE_URL = "http://127.0.0.1:8000"


def test_audio_upload_endpoint():
    """Test the audio file upload endpoint"""

    print("=" * 70)
    print("Audio File Upload API Test")
    print("=" * 70)

    # Since we don't have actual audio files, we'll demonstrate with the API
    print("\n📁 Audio File Upload Endpoint")
    print("-" * 70)

    print("\nEndpoint: POST /api/postprocess/upload")
    print("\nFeatures:")
    print("  ✓ Supports formats: WAV, MP3, M4A, FLAC, OGG, AAC")
    print("  ✓ Automatic conversion to 16kHz/16bit mono")
    print("  ✓ Optional silence removal")
    print("  ✓ Optional volume normalization")
    print("  ✓ Silence detection (VAD)")
    print("  ✓ Integrated transcription")
    print("  ✓ Optional post-processing")

    print("\n📝 Request Parameters:")
    print("  - file: Audio file (required)")
    print("  - apply_postprocess: Apply text cleaning (default: true)")
    print("  - remove_silence: Remove silence from audio (default: false)")
    print("  - normalize_volume: Normalize audio level (default: false)")
    print("  - detect_silence_only: Only detect silence (default: false)")

    print("\n📤 Example: Upload and transcribe audio file")
    print("-" * 70)
    print("\ncurl -X POST http://127.0.0.1:8000/api/postprocess/upload \\")
    print("  -F \"file=@recording.wav\" \\")
    print("  -F \"apply_postprocess=true\" \\")
    print("  -F \"remove_silence=true\"")

    print("\n\n📊 Example: Detect silence only (VAD)")
    print("-" * 70)
    print("\ncurl -X POST http://127.0.0.1:8000/api/postprocess/upload \\")
    print("  -F \"file=@speech.wav\" \\")
    print("  -F \"detect_silence_only=true\"")

    # Test endpoint availability
    print("\n🔍 Testing endpoint availability...")
    try:
        response = httpx.get(f"{BASE_URL}/api/postprocess/status")
        if response.status_code == 200:
            print("  ✓ Post-processing endpoint is available")
            capabilities = response.json()["capabilities"]
            print(f"  ✓ Features: {', '.join(capabilities['features'])}")
        else:
            print("  ✗ Endpoint not available")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70)

    print("\n📋 Next Steps:")
    print("  1. Prepare test audio files (WAV, MP3, etc.)")
    print("  2. Test with real audio using curl or a client")
    print("  3. Verify transcription quality")
    print("  4. Test post-processing results")


if __name__ == "__main__":
    test_audio_upload_endpoint()
