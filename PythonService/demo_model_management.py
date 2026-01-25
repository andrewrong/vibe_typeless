#!/usr/bin/env python3
"""
Demonstrate Model Management API
Show how to dynamically switch between different model sizes
"""

import httpx
import time
import json

BASE_URL = "http://127.0.0.1:8000"


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def demo_model_management():
    """Demonstrate model management features"""

    print_section("🎙️  Model Management API Demo")

    client = httpx.Client(base_url=BASE_URL)

    # 1. Check current configuration
    print("\n1️⃣  Current Configuration")
    print("-" * 70)

    response = client.get("/api/asr/config")
    config = response.json()

    print(f"Current Model: {config['current_model']}")
    print(f"Language: {config['language'] or 'Auto-detect'}")
    print(f"FP16: {config['fp16']}")
    print(f"Available Models: {', '.join(config['available_models'])}")

    # 2. List all available models with details
    print("\n2️⃣  Available Models")
    print("-" * 70)

    response = client.get("/api/asr/models")
    models = response.json()

    for size, info in models.items():
        print(f"\n{size.upper()}:")
        print(f"  Parameters: {info['params']}")
        print(f"  Download: {info['download_size']}")
        print(f"  RAM Required: {info['ram_required']}")
        print(f"  Speed: {info['speed']}")
        print(f"  Description: {info['description']}")

    # 3. Get detailed info for a specific model
    print("\n3️⃣  Model Details (Tiny)")
    print("-" * 70)

    response = client.get("/api/asr/models/tiny")
    tiny_info = response.json()

    print(f"Size: {tiny_info['size']}")
    print(f"Parameters: {tiny_info['params']}")
    print(f"Download Size: {tiny_info['download_size']}")
    print(f"RAM Required: {tiny_info['ram_required']}")
    print(f"Speed: {tiny_info['speed']}")
    print(f"Description: {tiny_info['description']}")

    # 4. Switch model (with confirmation)
    print("\n4️⃣  Switch Model")
    print("-" * 70)

    print("\nSwitching to 'tiny' model for faster processing...")
    start = time.time()

    response = client.post(
        "/api/asr/config",
        json={"model_size": "tiny"}
    )

    elapsed = time.time() - start

    if response.status_code == 200:
        config = response.json()
        print(f"✅ Model switched successfully ({elapsed:.2f}s)")
        print(f"   New model: {config['current_model']}")

    # 5. Test transcription with new model
    print("\n5️⃣  Test Transcription with Tiny Model")
    print("-" * 70)

    # Use the test audio we created earlier
    import os
    if os.path.exists("test_audio.wav"):
        print("Testing with test_audio.wav...")

        with open("test_audio.wav", "rb") as f:
            audio_data = f.read()

        start = time.time()
        response = client.post(
            "/api/asr/transcribe",
            content=audio_data,
            headers={"Content-Type": "application/octet-stream"},
            timeout=60
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Transcription complete ({elapsed:.2f}s)")
            print(f"   Transcript: \"{result['transcript']}\"")
            print(f"   Duration: {result['duration']:.2f}s")
            print(f"   RTF: {elapsed / result['duration']:.2f}x")
    else:
        print("⚠️  test_audio.wav not found")

    # 6. Reset to base model
    print("\n6️⃣  Reset to Default Model")
    print("-" * 70)

    print("Resetting to base model...")
    response = client.post("/api/asr/reset")

    if response.status_code == 200:
        config = response.json()
        print(f"✅ Reset successful")
        print(f"   Current model: {config['current_model']}")

    # 7. Show usage examples
    print("\n7️⃣  Usage Examples")
    print("-" * 70)

    print("\n# Python Client:")
    print("```python")
    print("import httpx")
    print()
    print("client = httpx.Client(base_url='http://127.0.0.1:8000')")
    print()
    print("# Get current config")
    print("config = client.get('/api/asr/config').json()")
    print("print(f\"Current model: {config['current_model']}\")")
    print()
    print("# Switch to tiny model (faster)")
    print("client.post('/api/asr/config', json={'model_size': 'tiny'})")
    print()
    print("# Switch to small model (better accuracy)")
    print("client.post('/api/asr/config', json={'model_size': 'small'})")
    print("```")

    print("\n# cURL:")
    print("# Get current config")
    print("curl http://127.0.0.1:8000/api/asr/config")
    print()
    print("# Switch to tiny model")
    print("curl -X POST http://127.0.0.1:8000/api/asr/config \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"model_size\": \"tiny\"}'")
    print()
    print("# List all models")
    print("curl http://127.0.0.1:8000/api/asr/models")

    print("\n" + "=" * 70)
    print("✅ Demo Complete!")
    print("=" * 70)

    print("\n💡 Tips:")
    print("  • Use 'tiny' for fast testing/development")
    print("  • Use 'base' for balanced performance (default)")
    print("  • Use 'small' or 'medium' for better accuracy")
    print("  • Use 'large' for best accuracy (if you have enough RAM)")
    print("  • Model is cached after first use")
    print("  • Switching model is instant (no download if cached)")

    print("\n📊 Performance Comparison:")
    print("  Model  | Params | Speed    | RAM  | Best For")
    print("  -------|-------|----------|------|----------")
    print("  tiny   | 39M   | ⚡⚡⚡ Fastest  | 1GB  | Testing")
    print("  base   | 74M   | ⚡⚡ Fast    | 1GB  | Daily use")
    print("  small  | 244M  | ⚡ Fast     | 2GB  | Production")
    print("  medium | 769M  | 🐢 Moderate | 5GB  | High quality")
    print("  large  | 1.5B  | 🐌 Slow     | 10GB | Best quality")


if __name__ == "__main__":
    try:
        demo_model_management()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
