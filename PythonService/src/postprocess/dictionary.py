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

        # ========== Financial & Stock Market Terms ==========

        # Investment products (English abbreviations)
        DictionaryEntry("etf", "ETF", "finance", case_sensitive=False),
        DictionaryEntry("etr", "ETF", "finance", case_sensitive=False),  # 常见误读
        DictionaryEntry("lof", "LOF", "finance", case_sensitive=False),
        DictionaryEntry("reits", "REITs", "finance", case_sensitive=False),

        # Stock metrics
        DictionaryEntry("pe", "PE", "finance", case_sensitive=False),  # 市盈率
        DictionaryEntry("pb", "PB", "finance", case_sensitive=False),  # 市净率
        DictionaryEntry("roe", "ROE", "finance", case_sensitive=False),  # 净资产收益率
        DictionaryEntry("roc", "ROC", "finance", case_sensitive=False),  # 变动率指标
        DictionaryEntry("eps", "EPS", "finance", case_sensitive=False),  # 每股收益
        DictionaryEntry("bps", "BPS", "finance", case_sensitive=False),  # 每股净资产
        DictionaryEntry("capm", "CAPM", "finance", case_sensitive=False),  # 资本资产定价模型

        # Stock market terms
        DictionaryEntry("ipo", "IPO", "finance", case_sensitive=False),  # 首次公开募股
        DictionaryEntry("a股", "A股", "finance", case_sensitive=False),
        DictionaryEntry("b股", "B股", "finance", case_sensitive=False),
        DictionaryEntry("h股", "H股", "finance", case_sensitive=False),
        DictionaryEntry("美股", "美股", "finance"),
        DictionaryEntry("港股", "港股", "finance"),
        DictionaryEntry("新三板", "新三板", "finance"),
        DictionaryEntry("科创板", "科创板", "finance"),
        DictionaryEntry("创业板", "创业板", "finance"),
        DictionaryEntry("北交所", "北交所", "finance"),

        # Trading terms
        DictionaryEntry("做多", "做多", "finance"),
        DictionaryEntry("做空", "做空", "finance"),
        DictionaryEntry("多头", "多头", "finance"),
        DictionaryEntry("空头", "空头", "finance"),
        DictionaryEntry("仓位", "仓位", "finance"),
        DictionaryEntry("满仓", "满仓", "finance"),
        DictionaryEntry("空仓", "空仓", "finance"),
        DictionaryEntry("半仓", "半仓", "finance"),
        DictionaryEntry("补仓", "补仓", "finance"),
        DictionaryEntry("减仓", "减仓", "finance"),
        DictionaryEntry("平仓", "平仓", "finance"),
        DictionaryEntry("爆仓", "爆仓", "finance"),
        DictionaryEntry("斩仓", "斩仓", "finance"),
        DictionaryEntry("止损", "止损", "finance"),
        DictionaryEntry("止盈", "止盈", "finance"),
        DictionaryEntry("杠杆", "杠杆", "finance"),
        DictionaryEntry("杠杆率", "杠杆率", "finance"),

        # Options & derivatives
        DictionaryEntry("期权", "期权", "finance"),
        DictionaryEntry("期货", "期货", "finance"),
        DictionaryEntry("股指期货", "股指期货", "finance"),
        DictionaryEntry("看涨期权", "看涨期权", "finance"),
        DictionaryEntry("看跌期权", "看跌期权", "finance"),
        DictionaryEntry("认购期权", "认购期权", "finance"),
        DictionaryEntry("认沽期权", "认沽期权", "finance"),
        DictionaryEntry("行权价", "行权价", "finance"),
        DictionaryEntry("到期日", "到期日", "finance"),

        # Valuation metrics
        DictionaryEntry("市盈率", "市盈率", "finance"),
        DictionaryEntry("市净率", "市净率", "finance"),
        DictionaryEntry("市销率", "市销率", "finance"),
        DictionaryEntry("股息率", "股息率", "finance"),
        DictionaryEntry("分红率", "分红率", "finance"),
        DictionaryEntry("收益率", "收益率", "finance"),
        DictionaryEntry("回报率", "回报率", "finance"),
        DictionaryEntry("换手率", "换手率", "finance"),
        DictionaryEntry("振幅", "振幅", "finance"),
        DictionaryEntry("涨跌幅", "涨跌幅", "finance"),

        # Economic indicators (English abbreviations)
        DictionaryEntry("cpi", "CPI", "economics", case_sensitive=False),  # 消费者物价指数
        DictionaryEntry("ppi", "PPI", "economics", case_sensitive=False),  # 生产者物价指数
        DictionaryEntry("gdp", "GDP", "economics", case_sensitive=False),  # 国内生产总值
        DictionaryEntry("pmi", "PMI", "economics", case_sensitive=False),  # 采购经理指数
        DictionaryEntry("m2", "M2", "economics", case_sensitive=False),    # 广义货币供应量
        DictionaryEntry("m1", "M1", "economics", case_sensitive=False),    # 狭义货币供应量

        # Trading strategies
        DictionaryEntry("价值投资", "价值投资", "finance"),
        DictionaryEntry("成长投资", "成长投资", "finance"),
        DictionaryEntry("定投", "定投", "finance"),
        DictionaryEntry("分批建仓", "分批建仓", "finance"),
        DictionaryEntry("金字塔建仓", "金字塔建仓", "finance"),
        DictionaryEntry("倒金字塔建仓", "倒金字塔建仓", "finance"),

        # Technical analysis
        DictionaryEntry("均线", "均线", "finance"),
        DictionaryEntry("五日线", "5日线", "finance"),
        DictionaryEntry("十日线", "10日线", "finance"),
        DictionaryEntry("二十日线", "20日线", "finance"),
        DictionaryEntry("六十日线", "60日线", "finance"),
        DictionaryEntry("年线", "年线", "finance"),
        DictionaryEntry("支撑位", "支撑位", "finance"),
        DictionaryEntry("阻力位", "阻力位", "finance"),
        DictionaryEntry("压力位", "压力位", "finance"),
        DictionaryEntry("突破", "突破", "finance"),
        DictionaryEntry("回调", "回调", "finance"),
        DictionaryEntry("反弹", "反弹", "finance"),

        # Market sentiment
        DictionaryEntry("牛市", "牛市", "finance"),
        DictionaryEntry("熊市", "熊市", "finance"),
        DictionaryEntry("震荡市", "震荡市", "finance"),
        DictionaryEntry("结构性行情", "结构性行情", "finance"),
        DictionaryEntry("板块轮动", "板块轮动", "finance"),

        # Stock types
        DictionaryEntry("蓝筹股", "蓝筹股", "finance"),
        DictionaryEntry("成长股", "成长股", "finance"),
        DictionaryEntry("价值股", "价值股", "finance"),
        DictionaryEntry("周期股", "周期股", "finance"),
        DictionaryEntry("题材股", "题材股", "finance"),
        DictionaryEntry("概念股", "概念股", "finance"),
        DictionaryEntry("龙头股", "龙头股", "finance"),
        DictionaryEntry("权重股", "权重股", "finance"),
        DictionaryEntry("小盘股", "小盘股", "finance"),
        DictionaryEntry("中盘股", "中盘股", "finance"),
        DictionaryEntry("大盘股", "大盘股", "finance"),
        DictionaryEntry("微盘股", "微盘股", "finance"),
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
