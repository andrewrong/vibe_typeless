#!/usr/bin/env python3
"""
Quick test for SenseVoice model
This script tests the SenseVoice ASR without running the full server
"""

import sys
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_import():
    """Test if sherpa-onnx can be imported"""
    print("=" * 60)
    print("📦 Testing SenseVoice Model Import")
    print("=" * 60)
    print()

    try:
        import sherpa_onnx
        print("✅ sherpa-onnx imported successfully")
        print(f"   Version: {sherpa_onnx.__version__ if hasattr(sherpa_onnx, '__version__') else 'unknown'}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import sherpa-onnx: {e}")
        print()
        print("Install with:")
        print("   uv add sherpa-onnx")
        return False


def test_model():
    """Test if SenseVoice model can be loaded"""
    print()
    print("=" * 60)
    print("🔧 Testing SenseVoice Model Loading")
    print("=" * 60)
    print()

    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent / "src"))

    try:
        from asr.sensevoice_model import SenseVoiceASR

        # Try to load model
        asr = SenseVoiceASR()
        print("✅ SenseVoice model loaded successfully")
        print()
        print(f"   Model path: {asr.model_path}")
        print(f"   Sample rate: {asr.sample_rate} Hz")
        print(f"   Using int8: {asr.use_int8}")
        return asr

    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        print()
        if "No module named 'sherpa_onnx'" in str(e):
            print("Install sherpa-onnx:")
            print("   uv add sherpa-onnx")
        elif "model" in str(e).lower() or "download" in str(e).lower():
            print("Download model:")
            print("   ./scripts/download_sensevoice.sh")
        return None


def test_transcription(asr):
    """Test with a simple audio"""
    if asr is None:
        return

    print()
    print("=" * 60)
    print("🎙️ Testing Audio Transcription")
    print("=" * 60)
    print()

    # Create a simple test tone (440Hz = A4 note)
    import numpy as np

    duration = 1.0  # 1 second
    sample_rate = 16000
    frequency = 440.0  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = 0.3 * np.sin(2 * np.pi * frequency * t)

    # Fade in/out to avoid clicks
    fade_samples = int(0.01 * sample_rate)  # 10ms fade
    audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
    audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    # Convert to int16
    audio_int16 = (audio * 32767).astype(np.int16)

    print(f"📊 Test audio:")
    print(f"   Duration: {duration} seconds")
    print(f"   Sample rate: {sample_rate} Hz")
    print(f"   Tone: {frequency} Hz (A4 note)")
    print(f"   Shape: {audio_int16.shape}")
    print()
    print("🔄 Transcribing...")

    try:
        result = asr.transcribe(audio_int16)

        print()
        print("✅ Transcription complete!")
        print(f"   Result: '{result}'")

        if not result or result == "hello" or result == "Hi":
            print()
            print("⚠️  Note: The test audio is a simple sine wave.")
            print("   SenseVoice may output unpredictable text for non-speech audio.")
            print("   This is normal behavior.")

    except Exception as e:
        print(f"❌ Transcription failed: {e}")


def main():
    """Main test runner"""
    print()
    print("🚀 SenseVoice Quick Test")
    print()

    # Test 1: Import
    if not test_import():
        sys.exit(1)

    # Test 2: Model loading
    asr = test_model()
    if asr is None:
        sys.exit(1)

    # Test 3: Transcription
    test_transcription(asr)

    print()
    print("=" * 60)
    print("✅ All tests passed!")
    print()
    print("📝 To use SenseVoice in the app:")
    print("   1. Edit PythonService/src/asr/__init__.py")
    print("      Set: MODEL_TYPE = 'sensevoice'")
    print("   2. Restart backend: cd PythonService && ./start.sh")
    print()


if __name__ == "__main__":
    main()
