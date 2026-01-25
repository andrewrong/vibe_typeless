"""
Tests for text post-processing
Following TDD principles - tests written first
"""

import pytest
from postprocess.processor import TextProcessor, ProcessResult


@pytest.fixture
def processor():
    """Create text processor instance"""
    return TextProcessor()


class TestFillerRemoval:
    """Test filler word removal"""

    def test_remove_basic_fillers(self, processor):
        """Test removing basic filler words"""
        text = "um hello uh this is a test"
        result = processor.remove_fillers(text)
        assert "um" not in result
        assert "uh" not in result
        assert "hello" in result

    def test_remove_common_fillers(self, processor):
        """Test removing common filler phrases"""
        text = "like you know actually sort of kind of test"
        result = processor.remove_fillers(text)
        assert "like" not in result or result.count("like") == 0
        assert "you know" not in result.lower()

    def test_preserve_content(self, processor):
        """Test that content words are preserved"""
        text = "The important meeting is at noon"
        result = processor.remove_fillers(text)
        assert "important meeting" in result.lower()
        assert "noon" in result


class TestDuplicateRemoval:
    """Test duplicate word removal"""

    def test_remove_stutter_duplicates(self, processor):
        """Test removing stutter repetitions"""
        text = "I I I think this is is is good"
        result = processor.remove_duplicates(text)
        # Should reduce repeated words
        assert result.count(" I ") <= 1
        assert result.count(" is ") <= 1

    def test_remove_phrase_repetition(self, processor):
        """Test removing repeated words in phrases"""
        text = "I think think that this is is good"
        result = processor.remove_duplicates(text)
        # Should remove word-level duplicates
        assert "think think" not in result
        # Check that consecutive "is" words are removed
        assert result != text  # Result should be different


class TestSelfCorrection:
    """Test self-correction detection"""

    def test_detect_correction(self, processor):
        """Test detecting self-correction patterns"""
        text = "Change it to red no actually blue"
        result = processor.apply_corrections(text)
        # Should detect "no actually" as correction
        assert "red" not in result or "blue" in result
        # The final choice should be blue
        assert result.lower().endswith("blue")

    def test_correction_phrases(self, processor):
        """Test various correction phrases"""
        test_cases = [
            ("It's red no I mean blue", "blue"),
            ("Make it red wait actually blue", "blue"),
            ("Red no blue", "blue"),
        ]
        for text, expected_word in test_cases:
            result = processor.apply_corrections(text)
            # Should contain the corrected word
            assert expected_word.lower() in result.lower()


class TestAutoFormatting:
    """Test automatic text formatting"""

    def test_format_list(self, processor):
        """Test formatting lists"""
        text = "first item second item third item"
        result = processor.auto_format(text)
        # Should detect as list
        assert "-" in result or "1." in result or "*" in result

    def test_format_numbered_list(self, processor):
        """Test formatting numbered sequences"""
        text = "first step second step third step"
        result = processor.auto_format(text)
        # Should format as numbered list
        assert "1." in result or "2." in result

    def test_preserve_paragraphs(self, processor):
        """Test that paragraph breaks are preserved"""
        text = "This is paragraph one.\n\nThis is paragraph two."
        result = processor.auto_format(text)
        # Should preserve paragraph breaks
        assert "\n\n" in result or "\n" in result


class TestFullProcessing:
    """Test complete text processing pipeline"""

    def test_process_comprehensive(self, processor):
        """Test full processing with all features"""
        text = "Um hello uh this is is a test no actually it's a demo"
        result = processor.process(text)

        assert isinstance(result, ProcessResult)
        assert result.original == text
        assert result.processed != text
        assert len(result.processed) <= len(result.original)

    def test_processing_stats(self, processor):
        """Test processing statistics"""
        text = "um like I I think this is is good"
        result = processor.process(text)

        assert hasattr(result, "stats")
        assert "fillers_removed" in result.stats
        assert "duplicates_removed" in result.stats
        assert "corrections_applied" in result.stats

    def test_empty_text(self, processor):
        """Test processing empty text"""
        result = processor.process("")
        assert result.processed == ""
        assert result.stats["total_changes"] == 0

    def test_minimal_changes(self, processor):
        """Test that clean text is minimally changed"""
        text = "This is a clean sentence without issues."
        result = processor.process(text)
        # Should be very similar to original
        assert result.stats["total_changes"] == 0


class TestCustomRules:
    """Test custom processing rules"""

    def test_add_custom_filler(self, processor):
        """Test adding custom filler words"""
        text = "custom word example test"
        processor.add_filler("custom word")
        result = processor.remove_fillers(text)
        assert "custom word" not in result

    def test_add_correction_phrase(self, processor):
        """Test adding custom correction phrases"""
        text = "first option or maybe second option"
        processor.add_correction_phrase("or maybe")
        result = processor.apply_corrections(text)
        # Should apply correction logic
        assert "first option" not in result or "second option" in result
