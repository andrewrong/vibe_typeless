#!/usr/bin/env python3
"""
Demonstrate API Improvements
Showcase new features: WebSocket streaming with progress, batch transcription, job queue
"""

import httpx
import asyncio
import json
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def generate_test_audio(filename, duration_seconds=5):
    """Generate a simple test audio file"""
    import numpy as np
    from pydub import AudioSegment
    from pydub.generators import Sine

    print(f"  Generating {duration_seconds}s test audio: {filename}")

    audio = AudioSegment.silent(duration=duration_seconds * 1000)

    # Add some tones
    for i in range(0, duration_seconds * 1000, 1000):
        tone = Sine(440).to_audio_segment(duration=500) - 10
        pos = min(i, len(audio) - len(tone))
        if pos >= 0:
            audio = audio.overlay(tone, position=pos)

    audio.export(filename, format="wav", parameters=["-ar", "16000", "-ac", "1"])
    print(f"  ✓ Created {filename}")


async def demo_batch_transcription():
    """Demonstrate batch transcription API"""

    print_section("📦 Batch Transcription API")

    client = httpx.Client(base_url=BASE_URL, timeout=300)

    # Generate multiple test files
    test_files = []
    for i in range(3):
        filename = f"test_batch_{i}.wav"
        generate_test_audio(filename, duration_seconds=5 + i * 2)
        test_files.append(filename)

    try:
        # Prepare files for upload
        files = [
            ("files", (filename, open(filename, "rb"), "audio/wav"))
            for filename in test_files
        ]

        print("\n📤 Submitting batch transcription request...")

        start = time.time()
        response = client.post(
            "/api/postprocess/batch-transcribe",
            files=files,
            params={
                "apply_postprocess": "true",
                "strategy": "auto"
            }
        )
        elapsed = time.time() - start

        # Close all file handles
        for _, file_tuple in files:
            file_tuple[1].close()

        if response.status_code == 200:
            result = response.json()

            print(f"✅ Batch transcription complete ({elapsed:.2f}s)")
            print(f"\n📊 Results:")
            print(f"  Total files: {result['total_files']}")
            print(f"  Successful: {result['successful']}")
            print(f"  Failed: {result['failed']}")
            print(f"  Total duration: {result['total_duration']:.1f}s")
            print(f"  Processing time: {result['processing_time']:.2f}s")
            print(f"  Speed: {result['processing_time'] / result['total_duration']:.2f}x RTF")

            print(f"\n📝 Individual Results:")
            for item in result['results']:
                if item['success']:
                    print(f"  ✓ {item['filename']}: {item['duration']:.1f}s")
                    if item.get('transcript'):
                        preview = item['transcript'][:50] + "..." if len(item['transcript']) > 50 else item['transcript']
                        print(f"    Transcript: \"{preview}\"")
                else:
                    print(f"  ✗ {item['filename']}: {item['error']}")

        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")

    finally:
        # Cleanup
        import os
        for filename in test_files:
            if os.path.exists(filename):
                os.unlink(filename)
        print(f"\n  Cleaned up test files")


def demo_job_queue():
    """Demonstrate job queue system"""

    print_section("🔄 Job Queue System")

    client = httpx.Client(base_url=BASE_URL, timeout=300)

    # Generate test audio
    filename = "test_job.wav"
    generate_test_audio(filename, duration_seconds=15)

    try:
        with open(filename, "rb") as f:
            files = {"file": (filename, f, "audio/wav")}

            print("\n📤 Submitting job to queue...")
            response = client.post(
                "/api/jobs/submit",
                files=files,
                params={
                    "strategy": "hybrid",
                    "apply_postprocess": "true"
                }
            )

        if response.status_code == 200:
            result = response.json()
            job_id = result['job_id']

            print(f"✅ Job submitted: {job_id}")
            print(f"   Status: {result['status']}")
            print(f"   Message: {result['message']}")

            # Poll for status
            print(f"\n⏳ Polling job status...")
            max_wait = 60  # seconds
            start = time.time()

            while time.time() - start < max_wait:
                response = client.get(f"/api/jobs/{job_id}")

                if response.status_code == 200:
                    job_info = response.json()

                    progress = job_info.get('progress', 0) * 100
                    status = job_info['status']

                    print(f"  Status: {status} | Progress: {progress:.0f}%")

                    if status in ['completed', 'failed', 'cancelled']:
                        print(f"\n✅ Job {status}")

                        if status == 'completed' and job_info.get('result'):
                            result_data = job_info['result']
                            print(f"\n📝 Result:")
                            print(f"  Transcript: {result_data.get('transcript', '')[:100]}...")
                            if result_data.get('processed_transcript'):
                                print(f"  Processed: {result_data['processed_transcript'][:100]}...")

                        break

                time.sleep(2)

            # Get queue stats
            response = client.get("/api/jobs/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"\n📊 Queue Stats:")
                print(f"  Total jobs: {stats['total_jobs']}")
                print(f"  Pending: {stats['pending']}")
                print(f"  Processing: {stats['processing']}")
                print(f"  Completed: {stats['completed']}")
                print(f"  Failed: {stats['failed']}")
                print(f"  Max concurrent: {stats['max_concurrent_jobs']}")

        else:
            print(f"❌ Error submitting job: {response.status_code}")
            print(f"   {response.text}")

    finally:
        # Cleanup
        import os
        if os.path.exists(filename):
            os.unlink(filename)
        print(f"\n  Cleaned up test file")


async def demo_websocket_progress():
    """Demonstrate WebSocket streaming with progress updates"""

    print_section("🌐 WebSocket Streaming with Progress")

    import websockets
    import json
    import asyncio

    uri = "ws://127.0.0.1:8000/api/asr/stream-progress"

    # Generate test audio
    filename = "test_stream.wav"
    generate_test_audio(filename, duration_seconds=10)

    try:
        print("\n🔌 Connecting to WebSocket...")
        print(f"   URI: {uri}")

        async with websockets.connect(uri) as websocket:
            print("✅ Connected")

            # Start session
            print("\n📤 Starting session...")
            await websocket.send(json.dumps({"action": "start"}))

            # Receive ready message
            response = await websocket.recv()
            data = json.loads(response)
            print(f"   Server: {data.get('type')} - {data.get('message', data.get('status', ''))}")

            # Read and send audio in chunks
            import numpy as np

            with open(filename, "rb") as f:
                audio_data = f.read()

            # Convert to numpy and split into chunks
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            chunk_size = 16000 * 2  # 2 seconds per chunk
            chunks = []

            for i in range(0, len(audio_array), chunk_size):
                chunk = audio_array[i:i + chunk_size]
                chunks.append(chunk)

            print(f"\n📤 Sending {len(chunks)} audio chunks...")

            for i, chunk in enumerate(chunks):
                await websocket.send(chunk.tobytes())

                # Receive acknowledgment
                response = await websocket.recv()
                data = json.loads(response)

                if data.get('type') == 'chunk_received':
                    print(f"  ✓ Chunk {i + 1}/{len(chunks)} received")

            # Request processing
            print("\n⏳ Requesting processing...")
            await websocket.send(json.dumps({
                "action": "process",
                "strategy": "hybrid",
                "apply_postprocess": "true"
            }))

            # Receive progress updates
            print("\n📊 Progress:")

            while True:
                response = await websocket.recv()
                data = json.loads(response)

                msg_type = data.get('type')

                if msg_type == 'progress':
                    current = data.get('current_segment', 0)
                    total = data.get('total_segments', 0)
                    percent = data.get('progress_percent', 0)
                    message = data.get('message', '')
                    print(f"  {percent:.0f}% - {message}")

                elif msg_type == 'segment_complete':
                    current = data.get('current_segment', 0)
                    total = data.get('total_segments', 0)
                    transcript = data.get('transcript_part', '')
                    print(f"  ✓ Segment {current}/{total} complete")
                    if transcript:
                        preview = transcript[:50] + "..." if len(transcript) > 50 else transcript
                        print(f"    \"{preview}\"")

                elif msg_type == 'complete':
                    print(f"\n✅ Processing complete!")
                    print(f"\n📝 Final Result:")
                    print(f"  Transcript: {data.get('final_transcript', '')[:100]}...")
                    print(f"  Processed: {data.get('processed_transcript', '')[:100]}...")
                    print(f"  Segments: {data.get('total_segments', 0)}")
                    print(f"  Duration: {data.get('duration', 0):.1f}s")
                    break

                elif msg_type == 'error':
                    print(f"\n❌ Error: {data.get('message')}")
                    break

    except Exception as e:
        print(f"\n❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        import os
        if os.path.exists(filename):
            os.unlink(filename)
        print(f"\n  Cleaned up test file")


def demo_rate_limiting():
    """Demonstrate rate limiting"""

    print_section("🚦 Rate Limiting")

    client = httpx.Client(base_url=BASE_URL)

    print("\n📤 Sending multiple requests to test rate limiting...")

    # Check health endpoint (high limit)
    print("\n1️⃣  Health check endpoint (1000 req/min):")
    for i in range(5):
        response = client.get("/health")
        print(f"  Request {i + 1}: {response.status_code}")

    # Check config endpoint (moderate limit)
    print("\n2️⃣  Config endpoint (60 req/min):")
    for i in range(5):
        response = client.get("/api/asr/config")
        print(f"  Request {i + 1}: {response.status_code}")

    print("\n✅ Rate limiting is active")
    print("💡 Try sending more than 60 requests/min to /api/asr/config to see 429 errors")


async def main():
    """Run all demos"""

    print_section("🎉 API Improvements Demo")

    print("""
This demo showcases the new API improvements:

1. 📦 Batch Transcription API
   - Process multiple audio files in a single request
   - Get all results at once
   - Automatic strategy selection (short vs long audio)

2. 🔄 Job Queue System
   - Submit long-running jobs
   - Poll for status updates
   - Get results when ready
   - View queue statistics

3. 🌐 WebSocket Streaming with Progress
   - Real-time progress updates
   - Segment-by-segment results
   - Better user experience for long files

4. 🚦 Rate Limiting
   - Protects against abuse
   - Different limits per endpoint
   - Graceful error handling

Starting demos...
    """)

    # Run demos
    try:
        await demo_batch_transcription()
        demo_job_queue()
        # await demo_websocket_progress()  # Requires websockets library
        demo_rate_limiting()

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")

    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

    print_section("Demo Complete")


if __name__ == "__main__":
    print("""
💡 Tips:

• Make sure the server is running:
  PYTHONPATH=src uv run uvicorn api.server:app --host 127.0.0.1 --port 8000

• Some demos may take a while to complete

• WebSocket demo requires: uv add websockets

• Rate limiting will show 429 errors if you exceed limits
    """)

    asyncio.run(main())
