"""
Tests for Personal Dictionary functionality
TDD Approach - Tests for dictionary management
"""

import sys
sys.path.insert(0, '/Volumes/nomoshen_macmini/data/project/self/typeless_2/PythonService')

import pytest
import tempfile
import json
from pathlib import Path
from src.postprocess.dictionary import DictionaryEntry, PersonalDictionary, personal_dictionary


class TestDictionaryEntry:
    """Test DictionaryEntry dataclass"""

    def test_create_entry(self):
        """Test creating a dictionary entry"""
        entry = DictionaryEntry(
            spoken="test",
            written="Test",
            category="tech",
            case_sensitive=True,
            whole_word=True
        )
        assert entry.spoken == "test"
        assert entry.written == "Test"
        assert entry.category == "tech"
        assert entry.case_sensitive is True
        assert entry.whole_word is True

    def test_create_entry_defaults(self):
        """Test creating entry with default values"""
        entry = DictionaryEntry(spoken="hello", written="Hello")
        assert entry.category == "general"
        assert entry.case_sensitive is False
        assert entry.whole_word is False

    def test_entry_to_dict(self):
        """Test converting entry to dict"""
        entry = DictionaryEntry(spoken="api", written="API", category="tech")
        data = entry.to_dict()
        assert data["spoken"] == "api"
        assert data["written"] == "API"
        assert data["category"] == "tech"


class TestPersonalDictionary:
    """Test PersonalDictionary class"""

    def test_create_dictionary(self):
        """Test creating dictionary"""
        dict_obj = PersonalDictionary()
        assert len(dict_obj.entries) > 0  # Has default entries

    def test_create_with_custom_path(self):
        """Test creating dictionary with custom path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "test_dict.json"
            dict_obj = PersonalDictionary(custom_path=custom_path)
            assert dict_obj.dictionary_path == custom_path

    def test_add_entry(self):
        """Test adding entry to dictionary"""
        dict_obj = PersonalDictionary()
        initial_count = len(dict_obj.entries)
        dict_obj.add_entry("custom", "Custom", "test")
        assert len(dict_obj.entries) == initial_count + 1

        # Check entry exists
        entry = dict_obj.entries[-1]
        assert entry.spoken == "custom"
        assert entry.written == "Custom"

    def test_add_duplicate_entry(self):
        """Test adding duplicate entry replaces old one"""
        dict_obj = PersonalDictionary()
        dict_obj.add_entry("unique", "Unique", "test")
        initial_count = len(dict_obj.entries)

        # Add duplicate
        dict_obj.add_entry("unique", "UNIQUE", "test2")
        assert len(dict_obj.entries) == initial_count  # Count unchanged

        # Check updated
        entry = [e for e in dict_obj.entries if e.spoken.lower() == "unique"][0]
        assert entry.written == "UNIQUE"

    def test_remove_entry(self):
        """Test removing entry"""
        dict_obj = PersonalDictionary()
        dict_obj.add_entry("remove", "Remove", "test")
        initial_count = len(dict_obj.entries)

        dict_obj.remove_entry("remove")
        assert len(dict_obj.entries) == initial_count - 1

    def test_remove_nonexistent_entry(self):
        """Test removing non-existent entry doesn't error"""
        dict_obj = PersonalDictionary()
        initial_count = len(dict_obj.entries)
        dict_obj.remove_entry("nonexistent")
        assert len(dict_obj.entries) == initial_count

    def test_apply_dictionary(self):
        """Test applying dictionary to text"""
        dict_obj = PersonalDictionary()
        # Add test entry
        dict_obj.add_entry("testword", "TestWord", "test")

        result = dict_obj.apply("This is a testword")
        assert "TestWord" in result

    def test_apply_case_insensitive(self):
        """Test case-insensitive matching"""
        dict_obj = PersonalDictionary()
        dict_obj.add_entry("api", "API", "tech", case_sensitive=False)

        result = dict_obj.apply("I need the api and API")
        assert result.count("API") == 2

    def test_apply_case_sensitive(self):
        """Test case-sensitive matching"""
        dict_obj = PersonalDictionary()
        dict_obj.add_entry("API", "Application", "tech", case_sensitive=True)

        result = dict_obj.apply("The api vs API")
        assert "api" in result  # lowercase not replaced
        assert "Application" in result  # uppercase replaced

    def test_apply_whole_word(self):
        """Test whole word matching"""
        dict_obj = PersonalDictionary()
        dict_obj.add_entry("api", "API", "tech", whole_word=True)

        result = dict_obj.apply("The api is great")
        assert "API" in result

        # Should not match partial word
        result2 = dict_obj.apply("The apilibrary is great")
        assert "apilibrary" in result2

    def test_get_entries_by_category(self):
        """Test getting entries by category"""
        dict_obj = PersonalDictionary()
        dict_obj.add_entry("test1", "Test1", "category_a")
        dict_obj.add_entry("test2", "Test2", "category_a")
        dict_obj.add_entry("test3", "Test3", "category_b")

        cat_a = dict_obj.get_entries_by_category("category_a")
        assert len(cat_a) >= 2

    def test_get_all_categories(self):
        """Test getting all categories"""
        dict_obj = PersonalDictionary()
        categories = dict_obj.get_all_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0

    def test_save_and_load(self):
        """Test saving and loading dictionary"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "dict.json"

            # Create and save
            dict1 = PersonalDictionary(custom_path)
            dict1.add_entry("custom", "Custom", "test")
            dict1.save_to_file()

            # Load in new instance
            dict2 = PersonalDictionary(custom_path)
            assert any(e.spoken == "custom" for e in dict2.entries)

    def test_clear_custom_entries(self):
        """Test clearing custom entries"""
        dict_obj = PersonalDictionary()
        dict_obj.add_entry("custom", "Custom", "test")
        dict_obj.clear_custom_entries()

        # Check custom entry removed
        assert not any(e.spoken == "custom" for e in dict_obj.entries)


class TestDictionaryFinancialTerms:
    """Test financial terms in default dictionary"""

    def test_finance_terms_exist(self):
        """Test that financial terms exist in default dictionary"""
        dict_obj = PersonalDictionary()
        finance_entries = dict_obj.get_entries_by_category("finance")
        assert len(finance_entries) > 0

    def test_stock_terms(self):
        """Test stock-related terms"""
        dict_obj = PersonalDictionary()
        result = dict_obj.apply("buy etf and lof today")
        assert "ETF" in result
        assert "LOF" in result

    def test_options_terms(self):
        """Test options trading terms protection"""
        dict_obj = PersonalDictionary()
        # Check that options terms exist
        entries = dict_obj.get_entries_by_category("finance")
        options = [e for e in entries if "put" in e.spoken.lower() or "call" in e.spoken.lower()]
        assert len(options) > 0


class TestDictionaryEdgeCases:
    """Test dictionary edge cases"""

    def test_empty_text(self):
        """Test applying to empty text"""
        dict_obj = PersonalDictionary()
        result = dict_obj.apply("")
        assert result == ""

    def test_none_text(self):
        """Test applying to None"""
        dict_obj = PersonalDictionary()
        result = dict_obj.apply(None)
        assert result is None

    def test_special_characters(self):
        """Test entries with special characters"""
        dict_obj = PersonalDictionary()
        dict_obj.add_entry("c++", "C++", "tech")
        result = dict_obj.apply("I love c++")
        assert "C++" in result

    def test_long_text_performance(self):
        """Test performance with long text"""
        dict_obj = PersonalDictionary()
        long_text = "testword " * 1000
        result = dict_obj.apply(long_text)
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
