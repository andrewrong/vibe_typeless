"""
SenseVoice ASR model using sherpa-onnx
Fast, accurate, multilingual speech recognition for macOS/Linux/Windows

Model: SenseVoice Small (228MB, >95% accuracy, millisecond latency)
Language: Chinese, English, Japanese, Korean, Cantonese
"""

import logging
from pathlib import Path
from typing import Optional, Dict
import numpy as np
import re

logger = logging.getLogger(__name__)

# Financial terms correction dictionary
# Maps common misrecognitions to correct financial terms
FINANCIAL_TERMS_CORRECTIONS: Dict[str, str] = {
    # Common Chinese misrecognitions of English financial terms
    "塞尔普特": "sell put",
    "塞尔帕特": "sell put",
    "卖put": "sell put",
    "卖普特": "sell put",
    "塞欧普特": "sell put",

    "塞尔扣": "sell call",
    "塞尔考": "sell call",
    "卖call": "sell call",
    "塞考": "sell call",

    "拜普特": "buy put",
    "买put": "buy put",

    "拜扣": "buy call",
    "买call": "buy call",

    "卡沃考": "covered call",
    "卡沃德扣": "covered call",

    "内克普特": "naked put",

    "斯拽克普莱斯": "strike price",
    "斯拽克": "strike",

    "普瑞米姆": "premium",
    "普瑞谬": "premium",

    "艾克思皮瑞神": "expiration",
    "艾克思皮": "expiration",

    "迪尔塔": "delta",
    "伽马": "gamma",
    "西塔": "theta",
    "维伽": "vega",

    "浪": "long",
    "肖特": "short",
    "牛市": "bullish",
    "熊市": "bearish",

    "迪威登": "dividend",
    "伊尔德": "yield",
    "玛金": "margin",
    "莱沃瑞吉": "leverage",

    "因泽莫尼": "in the money",
    "艾特泽莫尼": "at the money",
    "奥特泽莫尼": "out of the money",
}


class SenseVoiceASR:
    """
    SenseVoice ASR model (228MB, >95% accuracy, millisecond latency)

    Supports: Chinese, English, Japanese, Korean, Cantonese
    Uses: sherpa-onnx (ONNX Runtime - cross-platform)

    Performance:
        - 10 seconds audio processed in ~70ms
        - 15x faster than Whisper-Large
        - Better Chinese/Cantonese accuracy than Whisper

    Model files will be auto-downloaded on first run to:
        runtime/models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/
    """

    def __init__(self, model_path: Optional[str] = None, use_int8: bool = True, language: str = "auto"):
        """
        Initialize SenseVoice model

        Args:
            model_path: Path to model directory (auto-detect if None)
            use_int8: Use int8 quantized model (faster, slightly less accurate)
            language: Language code ("auto", "zh", "en", "ja", "ko", "yue")
        """
        # Auto-detect model path
        if model_path is None:
            model_path = self._find_model_path()

        model_path = Path(model_path)

        # Check if model files exist
        # Try int8 first, fallback to float32
        model_int8 = model_path / "model.int8.onnx"
        model_float32 = model_path / "model.onnx"

        if model_int8.exists():
            model_file = model_int8
        elif model_float32.exists():
            model_file = model_float32
            use_int8 = False
        else:
            # Default to int8 path (will be downloaded)
            model_file = model_int8

        tokens_file = model_path / "tokens.txt"

        if not model_file.exists():
            self._download_model(model_path)

        # Import sherpa-onnx (lazy import for faster startup)
        try:
            import sherpa_onnx
        except ImportError:
            raise ImportError(
                "sherpa-onnx not installed. Install with: uv add sherpa-onnx"
            )

        logger.info(f"📦 Loading SenseVoice model from {model_path}")
        logger.info(f"   Model: {model_file.name}")
        logger.info(f"   Tokens: {tokens_file}")

        # Create recognizer with specified language
        self.language = language if language != "auto" else ""
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(model_file),
            tokens=str(tokens_file),
            use_itn=True,  # Enable ITN for better Chinese punctuation
            debug=False,
            num_threads=4,  # Use 4 threads for M-series chips
            language=self.language,
        )

        self.model_path = model_path
        self.use_int8 = use_int8
        self.enable_term_correction = True  # Enable by default
        logger.info(f"   Language: {language if language else 'auto'}")
        logger.info(f"   Financial terms correction: enabled")

        logger.info("✅ SenseVoice model loaded successfully")

    def correct_financial_terms(self, text: str) -> str:
        """
        Correct common misrecognitions of English financial terms.

        This function handles cases where SenseVoice recognizes English financial
        terms as Chinese phonetic approximations.

        Args:
            text: Raw transcription text

        Returns:
            Text with corrected financial terms
        """
        if not text or not self.enable_term_correction:
            return text

        corrected = text

        # Apply corrections
        for wrong, correct in FINANCIAL_TERMS_CORRECTIONS.items():
            # Use word boundaries for Chinese characters
            # Match the wrong term as a whole word/phrase
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            corrected = pattern.sub(correct, corrected)

        # Log corrections if any were made
        if corrected != text:
            logger.info(f"📝 Terms corrected: '{text}' -> '{corrected}'")

        return corrected

    def _find_model_path(self) -> Path:
        """Find model directory in runtime/models"""
        # Try multiple possible locations
        possible_paths = [
            Path(__file__).parent.parent.parent / "runtime" / "models" / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
            Path(__file__).parent.parent.parent / "PythonService" / "runtime" / "models" / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17",
            Path.home() / ".sherpa-onnx" / "sense-voice",
        ]

        for path in possible_paths:
            if path.exists() and (path / "tokens.txt").exists():
                logger.info(f"📂 Found model at: {path}")
                return path

        # Return default path (will trigger download)
        default_path = possible_paths[0]
        logger.info(f"📂 Model not found, will download to: {default_path}")
        return default_path

    def _download_model(self, model_path: Path):
        """Download model files if not present"""
        model_path.mkdir(parents=True, exist_ok=True)

        logger.info("📥 Downloading SenseVoice model (228MB)...")

        import urllib.request
        import tarfile
        import tempfile

        # Download URL
        url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2"

        try:
            # Download to temp file
            with tempfile.NamedTemporaryFile(suffix=".tar.bz2", delete=False) as tmp_file:
                logger.info(f"   Downloading from {url}...")
                urllib.request.urlretrieve(url, tmp_file.name)

                # Extract
                logger.info(f"   Extracting to {model_path}...")
                with tarfile.open(tmp_file.name, "r:bz2") as tar:
                    tar.extractall(model_path)

                # Cleanup
                Path(tmp_file.name).unlink()

            logger.info("✅ Model downloaded successfully")

        except Exception as e:
            raise RuntimeError(
                f"Failed to download model: {e}\n"
                f"Please download manually from:\n{url}"
            )

    def transcribe(self, audio: np.ndarray, language: str = "auto") -> str:
        """
        Transcribe audio array to text

        Args:
            audio: numpy array of audio samples
                   - int16 PCM (common from audio capture)
                   - float32 normalized to [-1, 1]
            language: Language code ("auto", "zh", "en", "ja", "ko", "yue")
                      Note: SenseVoice auto-detects language, this is just a hint

        Returns:
            Transcribed text
        """
        # Convert int16 to float32 if needed
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        else:
            audio = audio.copy()

        # Ensure 1D array
        if len(audio.shape) > 1:
            audio = audio[:, 0]  # Use first channel

        # Create stream and process
        stream = self.recognizer.create_stream()
        stream.accept_waveform(16000, audio)  # SenseVoice expects 16kHz
        self.recognizer.decode_stream(stream)

        result = stream.result.text.strip()

        # Apply financial terms correction (without AI)
        if result and self.enable_term_correction:
            result = self.correct_financial_terms(result)

        if result:
            logger.debug(f"📝 SenseVoice result: '{result[:50]}...'")

        return result

    @property
    def sample_rate(self) -> int:
        """SenseVoice expects 16kHz audio"""
        # Get sample rate from recognizer config ( sherpa-onnx OfflineRecognizer doesn't have .sample_rate attribute)
        return self.recognizer.config.sample_rate if hasattr(self.recognizer, 'config') else 16000

    @property
    def config(self):
        """Return config object for compatibility"""
        class Config:
            # sherpa-onnx OfflineSenseVoiceModelConfig doesn't have all attributes
            # Return fixed values for compatibility
            sample_rate = 16000
            model_size = "sensevoice-small"
            language = ""  # Default empty = auto-detect
            fp16 = True
        return Config()


# Test
if __name__ == "__main__":
    import soundfile as sf

    print("📦 SenseVoice ASR Test")
    print("=" * 50)

    asr = SenseVoiceASR()

    # Create test audio (1 second of silence)
    test_audio = np.zeros(16000, dtype=np.float32)

    print(f"Sample rate: {asr.sample_rate}")
    print(f"Test transcribe: '{asr.transcribe(test_audio)}'")
