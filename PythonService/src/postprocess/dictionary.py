"""
Personal Dictionary for Custom Terminology
Inspired by VoiceInk's Personal Dictionary feature
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class DictionaryEntry:
    """Dictionary entry for word/phrase replacement"""
    spoken: str           # What you say
    written: str          # What should be written
    category: str = "general"  # Category (tech, company, etc.)
    case_sensitive: bool = False
    whole_word: bool = False  # Match whole word only

    def to_dict(self) -> dict:
        return asdict(self)


class PersonalDictionary:
    """
    Personal Dictionary for custom terminology

    Features:
    - Custom word/phrase replacements
    - Case sensitivity control
    - Whole word matching
    - Category organization
    - Persistent storage
    """

    # Default dictionary with common tech terms
    DEFAULT_ENTRIES = [
        # Tech terms (capitalization)
        DictionaryEntry("api", "API", "tech", case_sensitive=False),
        DictionaryEntry("docker", "Docker", "tech", case_sensitive=False),
        DictionaryEntry("kubernetes", "Kubernetes", "tech", case_sensitive=False),
        DictionaryEntry("git", "git", "tech", case_sensitive=False),  # Keep lowercase
        DictionaryEntry("github", "GitHub", "tech", case_sensitive=False),
        DictionaryEntry("python", "Python", "tech", case_sensitive=False),
        DictionaryEntry("javascript", "JavaScript", "tech", case_sensitive=False),
        DictionaryEntry("typescript", "TypeScript", "tech", case_sensitive=False),
        DictionaryEntry("swift", "Swift", "tech", case_sensitive=False),
        DictionaryEntry("rust", "Rust", "tech", case_sensitive=False),

        # Chinese tech companies
        DictionaryEntry("阿里云", "阿里云", "company"),
        DictionaryEntry("腾讯", "腾讯", "company"),
        DictionaryEntry("字节跳动", "字节跳动", "company"),
        DictionaryEntry("百度", "百度", "company"),
        DictionaryEntry("华为", "华为", "company"),

        # Common phrases
        DictionaryEntry("ai", "AI", "tech", case_sensitive=False),
        DictionaryEntry("ml", "ML", "tech", case_sensitive=False),
        DictionaryEntry("llm", "LLM", "tech", case_sensitive=False),
        DictionaryEntry("gpt", "GPT", "tech", case_sensitive=False),
    ]

    def __init__(self, custom_path: Optional[Path] = None):
        """
        Initialize personal dictionary

        Args:
            custom_path: Optional custom dictionary file path
        """
        self.entries: List[DictionaryEntry] = []
        self.dictionary_path = custom_path or self._get_default_path()

        # Load default entries
        self.entries = self.DEFAULT_ENTRIES.copy()

        # Load custom entries if file exists
        self._load_from_file()

        logger.info(f"PersonalDictionary loaded with {len(self.entries)} entries")

    def _get_default_path(self) -> Path:
        """Get default dictionary file path"""
        config_dir = Path.home() / ".config" / "typeless"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "dictionary.json"

    def _load_from_file(self):
        """Load custom entries from file"""
        if not self.dictionary_path.exists():
            logger.info("No custom dictionary file found")
            return

        try:
            with open(self.dictionary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            custom_entries = [
                DictionaryEntry(**entry)
                for entry in data.get('entries', [])
            ]

            self.entries.extend(custom_entries)
            logger.info(f"Loaded {len(custom_entries)} custom entries")

        except Exception as e:
            logger.error(f"Failed to load dictionary: {e}")

    def save_to_file(self):
        """Save dictionary to file"""
        try:
            data = {
                'entries': [entry.to_dict() for entry in self.entries]
            }

            with open(self.dictionary_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved {len(self.entries)} entries to {self.dictionary_path}")

        except Exception as e:
            logger.error(f"Failed to save dictionary: {e}")

    def add_entry(self, spoken: str, written: str,
                  category: str = "custom",
                  case_sensitive: bool = False,
                  whole_word: bool = False):
        """
        Add a new dictionary entry

        Args:
            spoken: What you say
            written: What should be written
            category: Entry category
            case_sensitive: Match case
            whole_word: Whole word only
        """
        entry = DictionaryEntry(
            spoken=spoken,
            written=written,
            category=category,
            case_sensitive=case_sensitive,
            whole_word=whole_word
        )

        # Remove existing entry with same spoken form
        self.entries = [e for e in self.entries if e.spoken.lower() != spoken.lower()]
        self.entries.append(entry)

        logger.info(f"Added dictionary entry: '{spoken}' → '{written}'")

    def remove_entry(self, spoken: str):
        """Remove entry by spoken form"""
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.spoken.lower() != spoken.lower()]
        removed = before - len(self.entries)

        if removed > 0:
            logger.info(f"Removed {removed} entries for '{spoken}'")

    def apply(self, text: str) -> str:
        """
        Apply dictionary replacements to text

        Args:
            text: Input text

        Returns:
            Text with replacements applied
        """
        if not text:
            return text

        result = text
        replacements_made = 0

        # Sort by length (longest first) to handle phrases before words
        sorted_entries = sorted(self.entries, key=lambda e: len(e.spoken), reverse=True)

        for entry in sorted_entries:
            # Prepare pattern
            if entry.whole_word:
                # Match whole word only
                pattern = r'\b' + re.escape(entry.spoken) + r'\b'
            else:
                # Match anywhere
                pattern = re.escape(entry.spoken)

            # Flags
            flags = 0 if entry.case_sensitive else re.IGNORECASE

            try:
                compiled = re.compile(pattern, flags)
                matches = compiled.findall(result)

                if matches:
                    result = compiled.sub(entry.written, result)
                    replacements_made += len(matches)

            except re.error as e:
                logger.warning(f"Invalid regex pattern for '{entry.spoken}': {e}")

        if replacements_made > 0:
            logger.info(f"Applied {replacements_made} dictionary replacements")

        return result

    def get_entries_by_category(self, category: str) -> List[DictionaryEntry]:
        """Get all entries in a category"""
        return [e for e in self.entries if e.category == category]

    def get_all_categories(self) -> List[str]:
        """Get all unique categories"""
        return list(set(e.category for e in self.entries))

    def clear_custom_entries(self):
        """Clear all custom entries, keep defaults"""
        self.entries = self.DEFAULT_ENTRIES.copy()
        logger.info("Cleared custom entries, keeping defaults")


# Global dictionary instance
personal_dictionary = PersonalDictionary()
