"""
中文标点符号纠正模块
基于语义和语气词识别正确的标点符号
"""
import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ChinesePunctuationCorrector:
    """中文标点符号纠正器"""

    # 问句标记词（句子开头或结尾）
    QUESTION_PATTERNS = [
        # 疑问词
        r'什么|怎么|为什么|哪儿|哪里|多少|几|哪个|哪些|谁|怎样|如何',
        # 疑问语气词（句尾）
        r'吗$|呢$|啊$',
        # 选择疑问
        r'还是|或者',
        # 疑问结构
        r'是不是|对不对|好不好|行不行|能不能|可不可以',
    ]

    # 感叹句标记词
    EXCLAMATION_PATTERNS = [
        r'太|真|好|非常|特别|相当|简直|竟然|居然|竟然',
        r'啊|呀|哇|哦|嘿|唉',
    ]

    # 陈述句标记（不应该使用问号）
    STATEMENT_PATTERNS = [
        r'说|告诉|表示|认为|觉得|以为|发现|知道',
        r'是.+的',
    ]

    def __init__(self):
        # 编译正则表达式
        self.question_regex = re.compile(
            '|'.join(self.QUESTION_PATTERNS),
            flags=re.IGNORECASE
        )
        self.exclamation_regex = re.compile(
            '|'.join(self.EXCLAMATION_PATTERNS),
            flags=re.IGNORECASE
        )
        self.statement_regex = re.compile(
            '|'.join(self.STATEMENT_PATTERNS),
            flags=re.IGNORECASE
        )

        # 常见错误标点映射
        self.error_mapping: Dict[str, str] = {
            '。？': '？',
            '？！': '！',
            '？！': '！',
        }

    def correct(self, text: str) -> str:
        """
        纠正中文标点符号

        Args:
            text: 原始文本

        Returns:
            纠正后的文本
        """
        if not text:
            return text

        logger.debug(f"Punctuation input: {text}")

        # 移除多余的空格
        text = re.sub(r'\s+', '', text)
        logger.debug(f"After removing spaces: {text}")

        # 分句处理（按已有标点分割）
        sentences = self._split_sentences(text)
        logger.debug(f"Split into {len(sentences)} sentences: {sentences}")

        corrected_sentences = []
        for sentence in sentences:
            corrected = self._correct_sentence(sentence)
            corrected_sentences.append(corrected)

        result = ''.join(corrected_sentences)
        logger.debug(f"Punctuation output: {result}")

        return result

    def _split_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        # 首先按已有标点分割
        if re.search(r'[。！？？！]', text):
            pattern = r'([^。！？？！]+[。！？？！]?)'
            sentences = re.findall(pattern, text)
            return [s for s in sentences if s.strip()]

        # 如果没有标点，首先检查是否有疑问语气词
        # 在"吗/呢/啊"后分割（这些通常是问句的结束）
        for particle in ['吗', '呢', '啊']:
            if particle in text:
                parts = text.split(particle, 1)  # 只在第一个处分割
                if len(parts) == 2:
                    first = (parts[0].strip() + particle)  # 将语气词保留在第一句末尾
                    second = parts[1].strip()
                    if first and second:
                        # 检查第二部分是否以连接词开头
                        connectors = ['但是', '不过', '而且', '另外', '还有', '所以', '因此', '我觉得', '我认为', '我想', '我现在']
                        for conn in connectors:
                            if second.startswith(conn):
                                return [first, second]
                        # 如果没有明显的连接词，仍然分割（可能是连续的短句）
                        if len(second) > 3:  # 确保第二部分不是太短
                            return [first, second]

        # 如果没有疑问语气词，尝试按连接词分割（保留连接词在第二句开头）
        connectors = ['但是', '不过', '而且', '另外', '还有', '所以', '因此', '我觉得', '我认为', '我想', '我现在']

        for conn in connectors:
            if conn in text:
                # 在连接词前分割
                parts = text.split(conn, 1)  # 只分割第一个
                if len(parts) == 2 and parts[0].strip():  # 确保第一部分不为空
                    return [parts[0].strip(), conn + parts[1].strip()]

        # 如果无法分割，返回整个文本
        return [text]

    def _correct_sentence(self, sentence: str) -> str:
        """
        纠正单个句子的标点

        Args:
            sentence: 单个句子（可能包含标点）

        Returns:
            纠正后的句子
        """
        logger.debug(f"Correcting sentence: {sentence!r}")

        # 如果句子没有结尾标点，添加句号
        if not sentence or sentence[-1] not in '。！？？！':
            punct = self._determine_punctuation(sentence)
            result = sentence + punct
            logger.debug(f"No ending punct, adding {punct!r}: {result!r}")
            return result

        # 如果已有标点，检查是否需要纠正
        last_char = sentence[-1]
        rest_of_sentence = sentence[:-1]

        # 根据句子内容判断应该用什么标点
        correct_punct = self._determine_punctuation(rest_of_sentence)

        # 只有当原有标点明显错误时才纠正
        if last_char in '。。' and correct_punct in '？！':
            return rest_of_sentence + correct_punct

        return sentence

    def _determine_punctuation(self, text: str) -> str:
        """
        根据文本内容确定应该使用的标点符号

        Args:
            text: 不含标点的文本

        Returns:
            应该使用的标点符号
        """
        # 首先检查句尾是否有疑问语气词（优先级最高）
        if re.search(r'[吗呢啊]$', text):
            return '？'

        # 检查是否包含问句标记
        question_match = self.question_regex.search(text)

        # 检查是否包含感叹句标记
        exclamation_match = self.exclamation_regex.search(text)

        # 优先级判断
        if question_match:
            # 检查是否是陈述句（例如："他告诉我为什么..."）
            # 只有当句子以"告诉/说/表示"开头时才可能是陈述句
            # "你觉得/我认为/我想"等后面接疑问词时，通常是问句
            direct_statement_patterns = [
                r'^(我|你|他|她|它|我们|你们|他们)(告诉|说|表示|发现)',
            ]
            is_direct_statement = any(re.search(p, text) for p in direct_statement_patterns)

            if not is_direct_statement:
                # 疑问词在前半部分，更可能是问句
                question_pos = question_match.start()
                if question_pos <= len(text) * 0.75:  # 疑问词在前 75%
                    return '？'

        if exclamation_match:
            # 如果有强烈感叹词
            exclamation_pos = exclamation_match.start()
            if exclamation_pos < len(text) * 0.8:
                return '！'

        # 默认使用句号
        return '。'

    def add_rule(self, pattern: str, punctuation: str):
        """
        添加自定义标点规则

        Args:
            pattern: 匹配模式（正则表达式）
            punctuation: 目标标点符号（。！？）
        """
        if punctuation == '？':
            self.QUESTION_PATTERNS.append(pattern)
            self.question_regex = re.compile(
                '|'.join(self.QUESTION_PATTERNS),
                flags=re.IGNORECASE
            )
        elif punctuation == '！':
            self.EXCLAMATION_PATTERNS.append(pattern)
            self.exclamation_regex = re.compile(
                '|'.join(self.EXCLAMATION_PATTERNS),
                flags=re.IGNORECASE
            )
        else:
            logger.warning(f"Unsupported punctuation: {punctuation}")
