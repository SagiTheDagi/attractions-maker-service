"""
Enums for attraction data models.
"""
from enum import Enum


class AttractionType(str, Enum):
    """Type of attraction."""
    ACTIVITY = "activity"
    RESTAURANT = "restaurant"
    MALL = "mall"
    STORE_CHAIN = "store_chain"


class PriceRange(str, Enum):
    """Price range for attractions."""
    FREE = "free"
    CHEAP = "cheap"
    EXPENSIVE = "expensive"
