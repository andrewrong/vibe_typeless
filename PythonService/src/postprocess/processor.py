"""
Text Post-Processing Module
Handles rule-based text cleaning and formatting
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from .punctuation import ChinesePunctuationCorrector


@dataclass
class ProcessResult:
    """Result of text processing"""
    original: str
    processed: str
    stats: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize stats if not provided"""
        if not self.stats:
            self.stats = {
                "fillers_removed": 0,
                "duplicates_removed": 0,
                "corrections_applied": 0,
                "total_changes": 0
            }


class TextProcessor:
    """
    Text processor for cleaning and formatting transcribed text

    Features:
    - Filler word removal
    - Duplicate word/phrase removal
    - Self-correction detection
    - Automatic formatting
    """

    # Default filler words and phrases
    DEFAULT_FILLERS = [
        "um", "uh", "er", "ah",
        "like", "you know", "actually",
        "sort of", "kind of",
        "I mean", "or something",
        "whatever", "etcetera"
    ]

    # Default correction phrases
    DEFAULT_CORRECTIONS = [
        "no actually", "wait actually", "no I mean",
        "no wait", "sorry I meant", "actually no",
        "no ", "no,", "no.", "no!"
    ]

    def __init__(self):
        """Initialize text processor"""
        self.fillers = set(self.DEFAULT_FILLERS)
        self.correction_phrases = set(self.DEFAULT_CORRECTIONS)
        self.punctuation_corrector = ChinesePunctuationCorrector()

    def add_filler(self, filler: str):
        """Add custom filler word"""
        self.fillers.add(filler.lower())

    def add_correction_phrase(self, phrase: str):
        """Add custom correction phrase"""
        self.correction_phrases.add(phrase.lower())

    def remove_fillers(self, text: str) -> str:
        """
        Remove filler words and phrases

        Args:
            text: Input text

        Returns:
            Text with fillers removed
        """
        if not text:
            return text

        result = text
        count = 0

        # Sort by length (longest first) to handle phrases before words
        sorted_fillers = sorted(self.fillers, key=len, reverse=True)

        for filler in sorted_fillers:
            # Case-insensitive replacement
            pattern = re.compile(r'\b' + re.escape(filler) + r'\b', re.IGNORECASE)
            matches = pattern.findall(result)
            count += len(matches)
            result = pattern.sub('', result)

        # Clean up extra spaces
        result = re.sub(r'\s+', ' ', result).strip()

        return result

    def remove_duplicates(self, text: str) -> str:
        """
        Remove duplicate words and phrases

        Args:
            text: Input text

        Returns:
            Text with duplicates removed
        """
        if not text:
            return text

        words = text.split()
        result = []
        prev_word = None
        count = 0

        for word in words:
            # Skip if same as previous word (case-insensitive)
            if prev_word and word.lower() == prev_word.lower():
                count += 1
                continue

            result.append(word)
            prev_word = word

        return ' '.join(result)

    def apply_corrections(self, text: str) -> str:
        """
        Detect and apply self-corrections

        Args:
            text: Input text

        Returns:
            Text with corrections applied
        """
        if not text:
            return text

        result = text
        count = 0

        for phrase in self.correction_phrases:
            if phrase.lower() in result.lower():
                # Find the correction and apply it
                pattern = re.compile(
                    r'([^.,!?]*?)\s+' + re.escape(phrase) + r'\s+([^.,!?]*?)([.,!?]|$)',
                    re.IGNORECASE
                )

                def replace_correction(match):
                    nonlocal count
                    count += 1
                    # Keep only the corrected part (after the correction phrase)
                    return match.group(2).strip() + match.group(3)

                result = pattern.sub(replace_correction, result)

        return result

    def auto_format(self, text: str) -> str:
        """
        Auto-format text based on patterns

        Args:
            text: Input text

        Returns:
            Formatted text
        """
        if not text:
            return text

        result = text

        # Detect list patterns (sequences like "first X, second Y, third Z")
        list_pattern = re.compile(
            r'\b(first|second|third|fourth|fifth|sixth|1st|2nd|3rd|4th|5th|6th)\s+([a-z]+)',
            re.IGNORECASE
        )

        if list_pattern.findall(result):
            # Format as numbered list
            items = list_pattern.findall(result)
            if len(items) > 1:
                # Replace with properly formatted list
                formatted_items = []
                for i, (ordinal, item) in enumerate(items, 1):
                    formatted_items.append(f"{i}. {item.capitalize()}")
                result = '\n'.join(formatted_items)

        # Preserve paragraph breaks
        result = re.sub(r'\n{3,}', '\n\n', result)

        return result

    def add_punctuation(self, text: str) -> str:
        """
        Add basic punctuation to Chinese text using rule-based approach

        Args:
            text: Input text without punctuation

        Returns:
            Text with punctuation added
        """
        if not text:
            return text

        result = text

        # Remove any existing punctuation first (to avoid duplicates)
        result = re.sub(r'[，。！？、；：""''（）《》【】]', '', result)

        # Split into sentences based on common pause words and patterns
        # These words typically indicate a pause or sentence boundary
        pause_words = ['然后', '接着', '之后', '所以', '但是', '不过', '而且', '另外',
                      '还有', '最后', '首先', '其次', '再次', '总之', '因此']

        # Split into segments
        segments = result.split()

        if not segments:
            return result

        # Add punctuation based on context
        punctuated = []
        for i, segment in enumerate(segments):
            punctuated.append(segment)

            # Add comma after pause words (but not at the end)
            if segment in pause_words and i < len(segments) - 1:
                punctuated.append('，')

            # Add period at the end
            if i == len(segments) - 1:
                punctuated.append('。')

        return ''.join(punctuated)

    def process(self, text: str) -> ProcessResult:
        """
        Apply full processing pipeline

        Args:
            text: Input text

        Returns:
            ProcessResult with processed text and stats
        """
        if not text:
            return ProcessResult(original=text, processed=text, stats={
                "fillers_removed": 0,
                "duplicates_removed": 0,
                "corrections_applied": 0,
                "total_changes": 0
            })

        stats = {
            "fillers_removed": 0,
            "duplicates_removed": 0,
            "corrections_applied": 0,
            "total_changes": 0
        }

        original_length = len(text)

        # Step 1: Remove fillers
        result = self.remove_fillers(text)
        stats["fillers_removed"] = original_length - len(result)

        # Step 2: Remove duplicates
        before_dup = len(result)
        result = self.remove_duplicates(result)
        stats["duplicates_removed"] = before_dup - len(result)

        # Step 3: Apply corrections
        before_corr = len(result)
        result = self.apply_corrections(result)
        stats["corrections_applied"] = before_corr - len(result)

        # Step 4: Auto-format
        result = self.auto_format(result)

        # Step 5: Correct punctuation
        result = self.punctuation_corrector.correct(result)

        # Calculate total changes
        stats["total_changes"] = sum([
            stats["fillers_removed"],
            stats["duplicates_removed"],
            stats["corrections_applied"]
        ])

        return ProcessResult(
            original=text,
            processed=result.strip(),
            stats=stats
        )
