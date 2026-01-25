#!/usr/bin/env python3
"""
Test script for full ASR + post-processing pipeline
"""

import httpx
import numpy as np
import json

BASE_URL = "http://127.0.0.1:8000"


def test_full_pipeline():
    """Test the complete ASR to post-processing pipeline"""

    print("=" * 60)
    print("Testing Full ASR + Post-Processing Pipeline")
    print("=" * 60)

    # Step 1: Start ASR session
    print("\n1. Starting ASR session...")
    response = httpx.post(f"{BASE_URL}/api/asr/start")
    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"   ✓ Session started: {session_id}")

    # Step 2: Create mock audio data (simulating speech)
    print("\n2. Creating mock audio data (simulating speech)...")
    # Create 1 second of audio at 16kHz
    sample_rate = 16000
    duration = 1  # second
    t = np.linspace(0, duration, sample_rate * duration)
    # Create a simple tone to represent audio
    audio_data = np.sin(2 * np.pi * 440 * t)  # 440Hz tone
    # Convert to int16
    audio_int16 = (audio_data * 32767).astype(np.int16)
    audio_bytes = audio_int16.tobytes()
    print(f"   ✓ Created {len(audio_bytes)} bytes of audio data")

    # Step 3: Send audio chunks
    print("\n3. Sending audio chunks for transcription...")
    response = httpx.post(
        f"{BASE_URL}/api/asr/audio/{session_id}",
        content=audio_bytes,
        headers={"Content-Type": "application/octet-stream"}
    )
    transcript_data = response.json()
    partial_transcript = transcript_data["partial_transcript"]
    print(f"   ✓ Partial transcript: '{partial_transcript}'")

    # Step 4: Stop session and get final transcript
    print("\n4. Stopping session and getting final transcript...")
    response = httpx.post(f"{BASE_URL}/api/asr/stop/{session_id}")
    final_data = response.json()
    final_transcript = final_data["final_transcript"]
    total_chunks = final_data["total_chunks"]
    print(f"   ✓ Final transcript: '{final_transcript}'")
    print(f"   ✓ Total audio chunks: {total_chunks}")

    # Step 5: Post-process the transcript
    print("\n5. Post-processing transcript...")
    process_request = {
        "text": final_transcript,
        "use_cloud_llm": False
    }
    response = httpx.post(
        f"{BASE_URL}/api/postprocess/text",
        json=process_request
    )
    processed_data = response.json()
    processed_text = processed_data["processed"]
    stats = processed_data["stats"]
    provider = processed_data["provider_used"]

    print(f"   ✓ Original: '{final_transcript}'")
    print(f"   ✓ Processed: '{processed_text}'")
    print(f"   ✓ Provider: {provider}")
    print(f"   ✓ Stats: {json.dumps(stats, indent=6)}")

    # Step 6: Test with a more realistic example
    print("\n6. Testing with realistic speech transcript...")
    realistic_text = "Um hello everyone uh this is is a test no actually it's a demonstration of our speech to text processing system"
    print(f"   Original: '{realistic_text}'")

    response = httpx.post(
        f"{BASE_URL}/api/postprocess/text",
        json={"text": realistic_text, "use_cloud_llm": False}
    )
    processed = response.json()
    print(f"   Processed: '{processed['processed']}'")
    print(f"   ✓ Fillers removed: {processed['stats']['fillers_removed']} chars")
    print(f"   ✓ Duplicates removed: {processed['stats']['duplicates_removed']} chars")

    # Step 7: Test the transcribe endpoint directly
    print("\n7. Testing direct file transcription endpoint...")
    response = httpx.post(
        f"{BASE_URL}/api/asr/transcribe",
        content=audio_bytes,
        headers={"Content-Type": "application/octet-stream"}
    )
    transcribe_data = response.json()
    print(f"   ✓ Transcript: '{transcribe_data['transcript']}'")
    print(f"   ✓ Duration: {transcribe_data['duration']:.3f} seconds")
    print(f"   ✓ Sample rate: {transcribe_data['sample_rate']} Hz")

    print("\n" + "=" * 60)
    print("Pipeline Test Complete!")
    print("=" * 60)

    return {
        "session_id": session_id,
        "transcript": final_transcript,
        "processed": processed_text,
        "stats": stats
    }


if __name__ == "__main__":
    try:
        result = test_full_pipeline()
        print("\n✅ All tests passed successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
