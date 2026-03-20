"""Tests for SenseVoice ASR model with traditional-to-simplified Chinese conversion."""

import sys
from unittest.mock import MagicMock, patch

# Mock sherpa_onnx before importing sensevoice_model
sherpa_mock = MagicMock()
sherpa_mock.OfflineRecognizer = MagicMock()
sherpa_mock.OfflineRecognizer.from_sense_voice = MagicMock(return_value=MagicMock())
sherpa_mock.OfflineRecognizer.from_sense_voice.return_value.config.sample_rate = 16000
sys.modules['sherpa_onnx'] = sherpa_mock


class TestSenseVoiceTraditionalToSimplified:
    """Tests for traditional to simplified Chinese conversion feature."""

    def test_to_simplified_chinese_converts_common_chars(self):
        """Test that common traditional Chinese characters are converted."""
        from src.asr.sensevoice_model import SenseVoiceASR

        # Create instance without actual model loading
        with patch.object(SenseVoiceASR, '_find_model_path', return_value='/fake/path'):
            with patch.object(SenseVoiceASR, '_download_model'):
                asr = SenseVoiceASR.__new__(SenseVoiceASR)
                asr.model_path = '/fake/path'
                asr.use_int8 = True
                asr.language = 'zh'
                asr.hotwords_file = None
                asr.hotwords_score = 1.5
                asr.recognizer = MagicMock()

                # Test conversion
                traditional_text = "這是一個測試，我們來看看效果。"
                expected_simplified = "这是一个测试，我们来看看效果。"

                result = asr._to_simplified_chinese(traditional_text)

                assert result == expected_simplified

    def test_to_simplified_chinese_handles_empty_string(self):
        """Test that empty string is handled gracefully."""
        from src.asr.sensevoice_model import SenseVoiceASR

        with patch.object(SenseVoiceASR, '_find_model_path', return_value='/fake/path'):
            with patch.object(SenseVoiceASR, '_download_model'):
                asr = SenseVoiceASR.__new__(SenseVoiceASR)
                asr.model_path = '/fake/path'
                asr.use_int8 = True
                asr.language = 'zh'
                asr.hotwords_file = None
                asr.hotwords_score = 1.5
                asr.recognizer = MagicMock()

                result = asr._to_simplified_chinese("")
                assert result == ""

    def test_to_simplified_chinese_handles_already_simplified(self):
        """Test that already simplified text remains unchanged."""
        from src.asr.sensevoice_model import SenseVoiceASR

        with patch.object(SenseVoiceASR, '_find_model_path', return_value='/fake/path'):
            with patch.object(SenseVoiceASR, '_download_model'):
                asr = SenseVoiceASR.__new__(SenseVoiceASR)
                asr.model_path = '/fake/path'
                asr.use_int8 = True
                asr.language = 'zh'
                asr.hotwords_file = None
                asr.hotwords_score = 1.5
                asr.recognizer = MagicMock()

                simplified_text = "这是一个测试。"
                result = asr._to_simplified_chinese(simplified_text)

                assert result == simplified_text

    def test_to_simplified_chinese_preserves_english_and_numbers(self):
        """Test that English and numbers are preserved."""
        from src.asr.sensevoice_model import SenseVoiceASR

        with patch.object(SenseVoiceASR, '_find_model_path', return_value='/fake/path'):
            with patch.object(SenseVoiceASR, '_download_model'):
                asr = SenseVoiceASR.__new__(SenseVoiceASR)
                asr.model_path = '/fake/path'
                asr.use_int8 = True
                asr.language = 'zh'
                asr.hotwords_file = None
                asr.hotwords_score = 1.5
                asr.recognizer = MagicMock()

                mixed_text = "這是API測試123。"
                expected = "这是API测试123。"

                result = asr._to_simplified_chinese(mixed_text)

                assert result == expected

    def test_converter_global_caching(self):
        """Test that converter uses module-level global cache."""
        from src.asr import sensevoice_model

        # Reset global cache
        original_converter = sensevoice_model._converter_instance
        sensevoice_model._converter_instance = None

        try:
            # First call should initialize
            converter1 = sensevoice_model._get_opencc_converter()
            assert converter1 is not None
            assert converter1 is not False

            # Second call should return same instance
            converter2 = sensevoice_model._get_opencc_converter()
            assert converter2 is converter1  # Same instance
        finally:
            # Restore original state
            sensevoice_model._converter_instance = original_converter

    def test_graceful_fallback_with_mocked_unavailable_opencc(self):
        """Test that original text is returned when opencc converter is unavailable."""
        from src.asr import sensevoice_model
        from src.asr.sensevoice_model import SenseVoiceASR

        # Reset and mock unavailable state
        original_converter = sensevoice_model._converter_instance
        sensevoice_model._converter_instance = False  # Mark as unavailable

        try:
            with patch.object(SenseVoiceASR, '_find_model_path', return_value='/fake/path'):
                with patch.object(SenseVoiceASR, '_download_model'):
                    asr = SenseVoiceASR.__new__(SenseVoiceASR)
                    asr.model_path = '/fake/path'
                    asr.use_int8 = True
                    asr.language = 'zh'
                    asr.hotwords_file = None
                    asr.hotwords_score = 1.5
                    asr.recognizer = MagicMock()

                    text = "這是測試"
                    result = asr._to_simplified_chinese(text)
                    # Should return original text when opencc not available
                    assert result == text
        finally:
            # Restore original state
            sensevoice_model._converter_instance = original_converter

    def test_transcribe_applies_conversion(self):
        """Test that transcribe method applies traditional to simplified conversion."""
        from src.asr import sensevoice_model
        from src.asr.sensevoice_model import SenseVoiceASR

        # Ensure converter is available
        original_converter = sensevoice_model._converter_instance
        sensevoice_model._converter_instance = None

        try:
            with patch.object(SenseVoiceASR, '_find_model_path', return_value='/fake/path'):
                with patch.object(SenseVoiceASR, '_download_model'):
                    asr = SenseVoiceASR.__new__(SenseVoiceASR)
                    asr.model_path = '/fake/path'
                    asr.use_int8 = True
                    asr.language = 'zh'
                    asr.hotwords_file = None
                    asr.hotwords_score = 1.5

                    # Mock recognizer and stream
                    mock_stream = MagicMock()
                    mock_stream.result.text = "這是一個測試"  # Traditional Chinese

                    mock_recognizer = MagicMock()
                    mock_recognizer.create_stream.return_value = mock_stream
                    asr.recognizer = mock_recognizer

                    # Call transcribe
                    import numpy as np
                    result = asr.transcribe(np.zeros(16000, dtype=np.float32))

                    # Should be converted to simplified
                    assert result == "这是一个测试"
        finally:
            # Restore original state
            sensevoice_model._converter_instance = original_converter
