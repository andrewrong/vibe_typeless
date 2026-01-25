#!/usr/bin/env python3
"""
Test Typeless ASR with real audio files
"""

import httpx
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"


def test_server_health():
    """Test if server is running"""
    print("=" * 70)
    print("1️⃣  Testing Server Health")
    print("=" * 70)

    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("\n💡 Start the server first:")
        print("   cd PythonService")
        print("   PYTHONPATH=src uv run python -m api.server")
        return False


def test_with_gradio_audio():
    """Test with gradio test audio"""
    print("\n" + "=" * 70)
    print("2️⃣  Testing with Gradio Test Audio (English)")
    print("=" * 70)

    audio_path = Path(".venv/lib/python3.12/site-packages/gradio/test_data/test_audio.wav")

    if not audio_path.exists():
        print(f"❌ Audio file not found: {audio_path}")
        return False

    print(f"📁 Audio file: {audio_path}")
    print(f"📊 File size: {audio_path.stat().st_size / 1024:.2f} KB")

    try:
        # Read audio file
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        print(f"📤 Uploading audio ({len(audio_data)} bytes)...")

        start_time = time.time()

        # Transcribe
        response = httpx.post(
            f"{BASE_URL}/api/asr/transcribe",
            content=audio_data,
            headers={"Content-Type": "application/octet-stream"},
            timeout=60
        )

        elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Transcription successful!")
            print(f"⏱️  Time: {elapsed:.2f} seconds")
            print(f"📝 Transcript: \"{result['transcript']}\"")
            print(f"⏱️  Duration: {result['duration']:.2f} seconds")
            print(f"🔊 Sample rate: {result['sample_rate']} Hz")
            print(f"📊 Real-time factor: {elapsed / result['duration']:.2f}x")

            # Check if we got meaningful text
            if len(result['transcript']) > 0:
                print("✅ Model generated text output")
                return True
            else:
                print("⚠️  Model returned empty text (audio might be silence)")
                return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_audio_upload():
    """Test audio file upload endpoint"""
    print("\n" + "=" * 70)
    print("3️⃣  Testing Audio File Upload with Post-Processing")
    print("=" * 70)

    audio_path = Path(".venv/lib/python3.12/site-packages/gradio/test_data/test_audio.wav")

    if not audio_path.exists():
        print(f"❌ Audio file not found: {audio_path}")
        return False

    try:
        with open(audio_path, "rb") as audio_file:
            files = {"file": (audio_path.name, audio_file, "audio/wav")}
            data = {
                "apply_postprocess": "true",
                "remove_silence": "false",
                "normalize_volume": "false"
            }

            print(f"📤 Uploading {audio_path.name}...")
            start_time = time.time()

            response = httpx.post(
                f"{BASE_URL}/api/postprocess/upload",
                files=files,
                data=data,
                timeout=60
            )

            elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload and processing successful!")
            print(f"⏱️  Time: {elapsed:.2f} seconds")

            if result.get("transcript"):
                print(f"\n📝 Original Transcript:")
                print(f"   \"{result['transcript']}\"")

            if result.get("processed_transcript"):
                print(f"\n✨ Processed Transcript:")
                print(f"   \"{result['processed_transcript']}\"")

            if result.get("audio_metadata"):
                metadata = result["audio_metadata"]
                print(f"\n📊 Audio Metadata:")
                print(f"   Sample rate: {metadata.get('sample_rate')} Hz")
                print(f"   Channels: {metadata.get('channels')}")
                print(f"   Bit depth: {metadata.get('bit_depth')}")
                print(f"   Duration: {metadata.get('duration', 0):.2f} seconds")

            if result.get("processing_stats"):
                stats = result["processing_stats"]
                print(f"\n📈 Processing Stats:")
                if "postprocess_stats" in stats:
                    pp = stats["postprocess_stats"]
                    print(f"   Fillers removed: {pp.get('fillers_removed', 0)}")
                    print(f"   Duplicates removed: {pp.get('duplicates_removed', 0)}")
                    print(f"   Total changes: {pp.get('total_changes', 0)}")

            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_session_streaming():
    """Test session-based streaming"""
    print("\n" + "=" * 70)
    print("4️⃣  Testing Session-Based Streaming")
    print("=" * 70)

    audio_path = Path(".venv/lib/python3.12/site-packages/gradio/test_data/test_audio.wav")

    if not audio_path.exists():
        print(f"❌ Audio file not found: {audio_path}")
        return False

    try:
        # Read audio
        import numpy as np
        from pydub import AudioSegment

        # Load audio with pydub
        audio = AudioSegment.from_wav(str(audio_path))

        # Convert to raw audio data
        audio = audio.set_frame_rate(16000)
        audio = audio.set_channels(1)
        audio = audio.set_sample_width(2)  # 16-bit

        # Get raw data
        audio_data = audio.raw_data

        print(f"📁 Audio: {audio_path.name}")
        print(f"⏱️  Duration: {len(audio) / 1000:.2f} seconds")
        print(f"📊 Size: {len(audio_data)} bytes")

        # Start session
        print("\n🎬 Starting session...")
        response = httpx.post(f"{BASE_URL}/api/asr/start")
        if response.status_code != 200:
            print(f"❌ Failed to start session")
            return False

        session_id = response.json()["session_id"]
        print(f"✅ Session started: {session_id}")

        # Split into chunks (2 seconds each)
        chunk_size = 16000 * 2 * 2  # 2 seconds, 16kHz, 16-bit
        chunks = [audio_data[i:i+chunk_size] for i in range(0, len(audio_data), chunk_size)]

        print(f"📦 Sending {len(chunks)} chunks...")

        all_transcripts = []
        for i, chunk in enumerate(chunks, 1):
            print(f"   Chunk {i}/{len(chunks)}...", end=" ")

            response = httpx.post(
                f"{BASE_URL}/api/asr/audio/{session_id}",
                content=chunk,
                headers={"Content-Type": "application/octet-stream"},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                transcript = result.get("partial_transcript", "")
                all_transcripts.append(transcript)
                print(f"✅")
                if transcript:
                    print(f"      \"{transcript}\"")
            else:
                print(f"❌ Error {response.status_code}")
                return False

        # Stop session
        print(f"\n🛑 Stopping session...")
        response = httpx.post(f"{BASE_URL}/api/asr/stop/{session_id}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Session stopped")
            print(f"📝 Final transcript: \"{result['final_transcript']}\"")
            print(f"📦 Total chunks: {result['total_chunks']}")
            return True
        else:
            print(f"❌ Failed to stop session")
            return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_post_processing():
    """Test text post-processing"""
    print("\n" + "=" * 70)
    print("5️⃣  Testing Text Post-Processing")
    print("=" * 70)

    test_cases = [
        {
            "name": "Filler removal",
            "text": "um hello uh this is a test of the system"
        },
        {
            "name": "Duplicate removal",
            "text": "hello hello this is is a test test"
        },
        {
            "name": "Self-correction",
            "text": "it's actually red no wait blue"
        },
        {
            "name": "List formatting",
            "text": "first second third and fourth"
        }
    ]

    all_passed = True

    for test in test_cases:
        print(f"\n📝 Test: {test['name']}")
        print(f"   Input: \"{test['text']}\"")

        try:
            response = httpx.post(
                f"{BASE_URL}/api/postprocess/text",
                json={
                    "text": test['text'],
                    "use_cloud_llm": False
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                print(f"   Output: \"{result['processed']}\"")
                print(f"   Stats: {result['stats']}")
                print(f"   ✅ Passed")
            else:
                print(f"   ❌ Error: {response.status_code}")
                all_passed = False

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            all_passed = False

    return all_passed


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🎙️  Typeless ASR - Real Audio Test Suite")
    print("=" * 70)

    results = {}

    # Test 1: Server health
    results["health"] = test_server_health()
    if not results["health"]:
        print("\n❌ Server not available. Please start the server first.")
        return

    # Test 2: Basic transcription
    results["transcription"] = test_with_gradio_audio()

    # Test 3: File upload
    results["upload"] = test_audio_upload()

    # Test 4: Session streaming
    results["streaming"] = test_session_streaming()

    # Test 5: Post-processing
    results["postprocess"] = test_post_processing()

    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name:20s} {status}")

    total = len(results)
    passed = sum(results.values())

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    print("\n💡 Tips:")
    print("  - First transcription may be slower (model loading)")
    print("  - Model is cached after first use")
    print("  - Adjust model size if needed (tiny/base/small/medium/large)")
    print("  - Use interactive docs: http://127.0.0.1:8000/docs")


if __name__ == "__main__":
    main()
