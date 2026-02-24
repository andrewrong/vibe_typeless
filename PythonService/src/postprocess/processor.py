"""
Text Post-Processing Module
Handles rule-based text cleaning and formatting
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from .punctuation import ChinesePunctuationCorrector
from .dictionary import PersonalDictionary


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
        # Load financial dictionary for term protection
        self.dictionary = PersonalDictionary()
        self.financial_terms = self.dictionary.entries  # Direct access to entries

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

    def protect_financial_terms(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        保护金融术语不被翻译或修改

        Args:
            text: 原始文本

        Returns:
            (保护后的文本, 占位符到原始术语的映射)
        """
        protected_text = text
        term_map = {}
        counter = 0

        # Get only English terms that need protection
        english_terms = [entry.written for entry in self.financial_terms
                        if self._is_english_term(entry.written)]

        # Sort by length descending to match longer terms first
        sorted_terms = sorted(english_terms, key=len, reverse=True)

        for term in sorted_terms:
            # Case-insensitive matching but preserve original case
            pattern = re.compile(re.escape(term), re.IGNORECASE)

            def replace_match(match):
                nonlocal counter
                original = match.group(0)
                placeholder = f"__TERM_{counter}__"
                term_map[placeholder] = original
                counter += 1
                return placeholder

            protected_text = pattern.sub(replace_match, protected_text)

        return protected_text, term_map

    def restore_financial_terms(self, text: str, term_map: Dict[str, str]) -> str:
        """
        还原被保护的金融术语

        Args:
            text: 处理后的文本
            term_map: 占位符到原始术语的映射

        Returns:
            还原后的文本
        """
        restored_text = text
        for placeholder, original_term in term_map.items():
            restored_text = restored_text.replace(placeholder, original_term)
        return restored_text

    def _is_english_term(self, term: str) -> bool:
        """检查术语是否为英文（需要保护）"""
        # Simple heuristic: if it contains spaces or common English patterns
        return bool(re.search(r'[a-zA-Z]{2,}', term))

    def process(self, text: str, mode: str = "standard") -> ProcessResult:
        """
        Apply processing pipeline with configurable mode

        Args:
            text: Input text
            mode: Processing mode - "none", "basic", "standard", "advanced"
                - none: No processing (fastest)
                - basic: Remove duplicates + punctuation correction only
                - standard: Full rule-based processing (default)
                - advanced: Standard + AI enhancement (slowest, best quality)

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

        # Mode: none - return as-is
        if mode == "none":
            return ProcessResult(original=text, processed=text, stats={
                "fillers_removed": 0,
                "duplicates_removed": 0,
                "corrections_applied": 0,
                "total_changes": 0,
                "mode": "none"
            })

        stats = {
            "fillers_removed": 0,
            "duplicates_removed": 0,
            "corrections_applied": 0,
            "total_changes": 0,
            "mode": mode
        }

        result = text

        # Mode: basic - minimal processing
        if mode == "basic":
            # Only remove duplicates and fix punctuation
            before_dup = len(result)
            result = self.remove_duplicates(result)
            stats["duplicates_removed"] = before_dup - len(result)
            result = self.punctuation_corrector.correct(result)
            stats["total_changes"] = stats["duplicates_removed"]
            return ProcessResult(original=text, processed=result.strip(), stats=stats)

        # Mode: standard or advanced - full rule-based processing
        original_length = len(text)

        # Step 1: Protect financial terms (preserve them during processing)
        result, term_map = self.protect_financial_terms(text)
        stats["terms_protected"] = len(term_map)

        # Step 2: Remove fillers
        result = self.remove_fillers(result)
        stats["fillers_removed"] = original_length - len(result)

        # Step 3: Remove duplicates
        before_dup = len(result)
        result = self.remove_duplicates(result)
        stats["duplicates_removed"] = before_dup - len(result)

        # Step 4: Apply corrections
        before_corr = len(result)
        result = self.apply_corrections(result)
        stats["corrections_applied"] = before_corr - len(result)

        # Step 5: Auto-format
        result = self.auto_format(result)

        # Step 6: Correct punctuation
        result = self.punctuation_corrector.correct(result)

        # Step 7: Restore financial terms
        result = self.restore_financial_terms(result, term_map)

        # Calculate total changes
        stats["total_changes"] = sum([
            stats.get("fillers_removed", 0),
            stats["duplicates_removed"],
            stats["corrections_applied"]
        ])

        return ProcessResult(
            original=text,
            processed=result.strip(),
            stats=stats
        )
