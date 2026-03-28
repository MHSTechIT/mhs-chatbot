"""
Convert numbers in text to English words for clearer TTS pronunciation.
When speaking Tamil content, numbers are converted to English words so ElevenLabs
pronounces them correctly (e.g., "15,000" -> "fifteen thousand", "4.8" -> "four point eight").
"""

import re
import logging

logger = logging.getLogger(__name__)


def _int_to_english(n: int) -> str:
    """Convert integer to English words using num2words."""
    try:
        from num2words import num2words
        return num2words(n, lang="en")
    except ImportError:
        return _int_to_english_fallback(n)


def _int_to_english_fallback(n: int) -> str:
    """Simple fallback if num2words not available."""
    if n < 0:
        return "minus " + _int_to_english_fallback(-n)
    if n == 0:
        return "zero"
    if n <= 19:
        words = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                 "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
                 "seventeen", "eighteen", "nineteen"]
        return words[n - 1]
    if n < 100:
        tens = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
        t, o = divmod(n, 10)
        return tens[t - 2] + (" " + _int_to_english_fallback(o) if o else "")
    if n < 1000:
        h, rest = divmod(n, 100)
        s = _int_to_english_fallback(h) + " hundred"
        return s + (" " + _int_to_english_fallback(rest) if rest else "")
    if n < 1_000_000:
        th, rest = divmod(n, 1000)
        s = _int_to_english_fallback(th) + " thousand"
        return s + (" " + _int_to_english_fallback(rest) if rest else "")
    return str(n)


def _decimal_to_english(s: str) -> str:
    """Convert decimal string like '4.8' to English words."""
    parts = s.split(".")
    int_part = _int_to_english(int(parts[0]))
    if len(parts) == 1:
        return int_part
    dec_digits = [_int_to_english(int(d)) for d in parts[1] if d.isdigit()]
    dec_part = " ".join(dec_digits)
    return int_part + " point " + dec_part if dec_part else int_part


def numbers_to_english_words(text: str) -> str:
    """
    Find all numbers (integers, decimals, numbers with commas) in text
    and replace them with English words for clearer TTS pronunciation.
    Used when speaking Tamil content - numbers are pronounced in English.
    """
    if not text or not text.strip():
        return text

    def replace_num(match):
        num_str = match.group(0).replace(",", "")
        try:
            if "." in num_str:
                return _decimal_to_english(num_str)
            return _int_to_english(int(num_str))
        except (ValueError, KeyError) as e:
            logger.warning(f"Could not convert number '{match.group(0)}' to English: {e}")
            return match.group(0)

    pattern = r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.\d+"
    result = re.sub(pattern, replace_num, text)
    return result
