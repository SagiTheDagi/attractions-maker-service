"""
Utilities for handling Hebrew text.
"""
import unicodedata
import re
from typing import Optional
from utils.logger import log


def normalize_hebrew(text: Optional[str]) -> Optional[str]:
    """
    Normalize Hebrew text to ensure consistent encoding.

    Args:
        text: Input text string

    Returns:
        Normalized text or None if input is None
    """
    if not text:
        return text

    # Normalize to NFC (Canonical Decomposition followed by Canonical Composition)
    normalized = unicodedata.normalize('NFC', text)

    # Remove extra whitespace
    normalized = ' '.join(normalized.split())

    return normalized


def contains_hebrew(text: str) -> bool:
    """
    Check if text contains Hebrew characters.

    Args:
        text: Input text string

    Returns:
        True if text contains Hebrew characters
    """
    if not text:
        return False

    # Hebrew Unicode range: \u0590-\u05FF
    hebrew_pattern = re.compile(r'[\u0590-\u05FF]')
    return bool(hebrew_pattern.search(text))


def extract_numbers_from_hebrew(text: str) -> list[int]:
    """
    Extract numbers from text that may contain Hebrew.

    Args:
        text: Input text string

    Returns:
        List of extracted numbers
    """
    if not text:
        return []

    # Find all numbers (including decimals)
    numbers = re.findall(r'\d+', text)
    return [int(n) for n in numbers]


def clean_hebrew_text(text: Optional[str]) -> Optional[str]:
    """
    Clean and prepare Hebrew text for storage.

    Args:
        text: Input text string

    Returns:
        Cleaned text or None if input is None
    """
    if not text:
        return text

    # Normalize
    cleaned = normalize_hebrew(text)

    # Remove control characters but preserve newlines and tabs
    cleaned = ''.join(char for char in cleaned if unicodedata.category(char)[0] != 'C' or char in '\n\t')

    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()

    return cleaned if cleaned else None


def detect_time_of_day_hebrew(text: str) -> Optional[str]:
    """
    Detect recommended time of day from Hebrew text.

    Args:
        text: Input text string

    Returns:
        Time of day ('morning', 'lunch', 'afternoon', 'evening', 'night') or None
    """
    if not text:
        return None

    text_lower = text.lower()

    # Hebrew time keywords
    if any(word in text_lower for word in ['בוקר', 'הבוקר']):
        return 'morning'
    elif any(word in text_lower for word in ['צהריים', 'הצהריים', 'ארוחת צהריים']):
        return 'lunch'
    elif any(word in text_lower for word in ['אחר הצהריים', 'אחה"צ']):
        return 'afternoon'
    elif any(word in text_lower for word in ['ערב', 'הערב', 'ערבית']):
        return 'evening'
    elif any(word in text_lower for word in ['לילה', 'הלילה']):
        return 'night'

    return None


def parse_duration_hebrew(text: str) -> Optional[int]:
    """
    Parse duration from Hebrew text and convert to minutes.

    Args:
        text: Input text containing duration information

    Returns:
        Duration in minutes or None if not found
    """
    if not text:
        return None

    text_lower = text.lower()

    # Pattern for hours (שעות or שעה)
    hours_pattern = r'(\d+(?:\.\d+)?)\s*(?:שעות|שעה|hours?)'
    hours_match = re.search(hours_pattern, text_lower)

    # Pattern for minutes (דקות or דקה)
    minutes_pattern = r'(\d+)\s*(?:דקות|דקה|minutes?)'
    minutes_match = re.search(minutes_pattern, text_lower)

    total_minutes = 0

    if hours_match:
        hours = float(hours_match.group(1))
        total_minutes += int(hours * 60)

    if minutes_match:
        minutes = int(minutes_match.group(1))
        total_minutes += minutes

    return total_minutes if total_minutes > 0 else None


def is_closed_hebrew(text: str) -> bool:
    """
    Check if text indicates the place is closed.

    Args:
        text: Input text string

    Returns:
        True if text indicates closed status
    """
    if not text:
        return False

    text_lower = text.lower()
    closed_keywords = ['סגור', 'סגורה', 'סגורים', 'closed']

    return any(keyword in text_lower for keyword in closed_keywords)


def extract_price_range_hebrew(text: str) -> Optional[str]:
    """
    Extract price range from Hebrew text.

    Args:
        text: Input text string

    Returns:
        Price range ('free', 'cheap', 'expensive') or None
    """
    if not text:
        return None

    text_lower = text.lower()

    # Check for free keywords
    free_keywords = ['חינם', 'ללא תשלום', 'בחינם', 'free']
    if any(keyword in text_lower for keyword in free_keywords):
        return 'free'

    # Count ₪ symbols
    shekel_count = text.count('₪')
    dollar_count = text.count('$')
    price_symbols = max(shekel_count, dollar_count)

    if price_symbols >= 3:
        return 'expensive'
    elif price_symbols >= 1:
        return 'cheap'

    # Check for expensive keywords
    expensive_keywords = ['יקר', 'יקרה', 'יקרים', 'expensive']
    if any(keyword in text_lower for keyword in expensive_keywords):
        return 'expensive'

    # Check for cheap keywords
    cheap_keywords = ['זול', 'זולה', 'זולים', 'cheap', 'inexpensive']
    if any(keyword in text_lower for keyword in cheap_keywords):
        return 'cheap'

    return None
