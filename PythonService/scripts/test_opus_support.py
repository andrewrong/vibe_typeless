#!/usr/bin/env python3
"""
Test OPUS audio support
Verify WhatsApp OPUS files can be loaded and transcribed
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_opus_loading():
    """Test OPUS file loading"""
    logger.info("=" * 60)
    logger.info("Testing OPUS Audio Support")
    logger.info("=" * 60)

    try:
        from src.asr.audio_processor import AudioProcessor

        processor = AudioProcessor()
        logger.info("✅ AudioProcessor initialized")

        # Check if test file exists
        test_files = [
            "load/WhatsApp Audio 2026-03-12 at 08.31.06.opus",
            "../load/WhatsApp Audio 2026-03-12 at 08.31.06.opus",
            "../../load/WhatsApp Audio 2026-03-12 at 08.31.06.opus",
        ]

        test_file = None
        for f in test_files:
            if Path(f).exists():
                test_file = f
                break

        if not test_file:
            logger.warning("⚠️  No OPUS test file found")
            logger.info("Expected file: load/WhatsApp Audio 2026-03-12 at 08.31.06.opus")
            return False

        logger.info(f"📁 Found test file: {test_file}")

        # Try to load the OPUS file
        logger.info("Loading OPUS file...")
        audio = processor.load_audio_file(file_path=test_file)
        logger.info(f"✅ OPUS file loaded successfully")
        logger.info(f"   Duration: {len(audio) / 1000:.2f}s")
        logger.info(f"   Channels: {audio.channels}")
        logger.info(f"   Sample rate: {audio.frame_rate}Hz")
        logger.info(f"   Frame width: {audio.frame_width}")

        # Convert to ASR format
        logger.info("\nConverting to ASR format...")
        audio_array, metadata = processor.convert_to_asr_format(audio)
        logger.info(f"✅ Conversion successful")
        logger.info(f"   Sample rate: {metadata['sample_rate']}Hz")
        logger.info(f"   Duration: {metadata['duration']:.2f}s")
        logger.info(f"   Array shape: {audio_array.shape}")
        logger.info(f"   Array dtype: {audio_array.dtype}")

        # Try to transcribe if model is available
        logger.info("\nTrying to transcribe...")
        try:
            from src.asr import get_asr_model

            model = get_asr_model(language="zh")
            audio_int16 = (audio_array * 32767).astype("int16")
            transcript = model.transcribe(audio_int16, language="zh")

            logger.info(f"✅ Transcription successful")
            logger.info(f"   Transcript: {transcript[:100]}...")

        except Exception as e:
            logger.warning(f"⚠️  Transcription failed (model may not be loaded): {e}")

        return True

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ffmpeg():
    """Check if ffmpeg is available"""
    import subprocess

    logger.info("\n" + "=" * 60)
    logger.info("Checking ffmpeg availability")
    logger.info("=" * 60)

    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            logger.info(f"✅ ffmpeg found: {version}")

            # Check if opus codec is supported
            result = subprocess.run(
                ['ffmpeg', '-codecs'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'opus' in result.stdout.lower():
                logger.info("✅ OPUS codec supported")
            else:
                logger.warning("⚠️  OPUS codec may not be supported")

            return True
        else:
            logger.error("❌ ffmpeg not working properly")
            return False
    except FileNotFoundError:
        logger.error("❌ ffmpeg not found. Please install ffmpeg:")
        logger.error("   brew install ffmpeg  # macOS")
        logger.error("   apt install ffmpeg   # Ubuntu/Debian")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking ffmpeg: {e}")
        return False


def main():
    """Main test"""
    logger.info("🧪 OPUS Audio Support Test")

    # Check ffmpeg first
    ffmpeg_ok = test_ffmpeg()

    if not ffmpeg_ok:
        logger.warning("\n⚠️  ffmpeg not available. pydub may still work if it has other backends.")

    # Test OPUS loading
    opus_ok = test_opus_loading()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    logger.info(f"ffmpeg: {'✅' if ffmpeg_ok else '❌'}")
    logger.info(f"OPUS loading: {'✅' if opus_ok else '❌'}")

    if opus_ok:
        logger.info("\n🎉 OPUS support is working!")
    else:
        logger.info("\n⚠️  OPUS support has issues. Check logs above.")

    return 0 if opus_ok else 1


if __name__ == "__main__":
    sys.exit(main())
