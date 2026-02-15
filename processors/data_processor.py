"""
Data processing and validation utilities.
"""
from typing import Dict, Optional
from models.enums import AttractionType, PriceRange
from utils.logger import log
from utils.hebrew_handler import clean_hebrew_text, normalize_hebrew


class DataProcessor:
    """Processes and validates scraped data."""

    @staticmethod
    def clean_data(data: Dict) -> Dict:
        """
        Clean and normalize scraped data.

        Args:
            data: Raw scraped data

        Returns:
            Cleaned data dictionary
        """
        cleaned = {}

        for key, value in data.items():
            if value is None:
                continue

            # Clean string values
            if isinstance(value, str):
                cleaned_value = clean_hebrew_text(value)
                if cleaned_value:
                    cleaned[key] = cleaned_value

            # Clean lists of strings
            elif isinstance(value, list) and value and isinstance(value[0], str):
                cleaned_list = [clean_hebrew_text(v) for v in value]
                cleaned_list = [v for v in cleaned_list if v]
                if cleaned_list:
                    cleaned[key] = cleaned_list

            # Keep other types as-is
            else:
                cleaned[key] = value

        return cleaned

    @staticmethod
    def infer_attraction_type(category: Optional[str], url: Optional[str]) -> Optional[AttractionType]:
        """
        Infer attraction type from category or URL.

        Args:
            category: Category text
            url: Google Maps URL

        Returns:
            AttractionType or None
        """
        if not category:
            return None

        category_lower = category.lower()

        # Restaurant keywords
        restaurant_keywords = [
            'restaurant', 'cafe', 'bar', 'bistro', 'diner', 'eatery',
            'מסעדה', 'בית קפה', 'בר', 'מזנון'
        ]
        if any(keyword in category_lower for keyword in restaurant_keywords):
            return AttractionType.RESTAURANT

        # Mall keywords
        mall_keywords = [
            'mall', 'shopping center', 'shopping centre',
            'קניון', 'מרכז קניות'
        ]
        if any(keyword in category_lower for keyword in mall_keywords):
            return AttractionType.MALL

        # Store chain keywords
        store_keywords = [
            'store', 'shop', 'supermarket', 'retail',
            'חנות', 'סופרמרקט', 'רשת'
        ]
        if any(keyword in category_lower for keyword in store_keywords):
            return AttractionType.STORE_CHAIN

        # Activity keywords (default)
        activity_keywords = [
            'park', 'museum', 'attraction', 'zoo', 'aquarium', 'theater',
            'פארק', 'מוזיאון', 'אטרקציה', 'גן חיות', 'תיאטרון'
        ]
        if any(keyword in category_lower for keyword in activity_keywords):
            return AttractionType.ACTIVITY

        # Default to activity
        return AttractionType.ACTIVITY

    @staticmethod
    def calculate_completeness(data: Dict, attraction_type: AttractionType) -> float:
        """
        Calculate completeness score for attraction data.

        Args:
            data: Attraction data
            attraction_type: Type of attraction

        Returns:
            Completeness score between 0 and 1
        """
        # Define required and optional fields by type
        common_fields = ['name', 'description', 'city', 'google_maps_url', 'lat', 'lng']
        optional_common = ['tags', 'hours', 'images', 'busy_days', 'closed_days', 'recommended_time']

        type_specific = {
            AttractionType.RESTAURANT: ['category', 'price_range', 'dietary_options', 'tickets_link'],
            AttractionType.ACTIVITY: ['category', 'duration', 'price_range', 'tickets_link'],
            AttractionType.MALL: ['category'],
            AttractionType.STORE_CHAIN: ['category', 'price_range'],
        }

        # Count present fields
        total_fields = len(common_fields) + len(optional_common) + len(type_specific.get(attraction_type, []))
        present_fields = 0

        for field in common_fields + optional_common + type_specific.get(attraction_type, []):
            if field in data and data[field]:
                present_fields += 1

        completeness = present_fields / total_fields if total_fields > 0 else 0

        return round(completeness, 2)

    @staticmethod
    def validate_coordinates(lat: Optional[float], lng: Optional[float]) -> bool:
        """
        Validate latitude and longitude coordinates.

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            True if coordinates are valid
        """
        if lat is None or lng is None:
            return False

        # Basic range validation
        if not (-90 <= lat <= 90):
            return False

        if not (-180 <= lng <= 180):
            return False

        return True

    @staticmethod
    def get_data_quality_info(data: Dict, attraction_type: AttractionType) -> Dict:
        """
        Calculate data quality information without modifying the data dict.

        Args:
            data: Attraction data
            attraction_type: Type of attraction

        Returns:
            Dict with completeness score and missing fields
        """
        completeness = DataProcessor.calculate_completeness(data, attraction_type)

        important_fields = ['name', 'description', 'city', 'lat', 'lng', 'hours']
        missing_fields = [field for field in important_fields if field not in data or not data[field]]

        return {
            'completeness': completeness,
            'missing_fields': missing_fields
        }

    @staticmethod
    def add_data_quality_info(data: Dict, attraction_type: AttractionType) -> Dict:
        """
        Add data quality information to the data.

        Args:
            data: Attraction data
            attraction_type: Type of attraction

        Returns:
            Data with quality info added
        """
        data['data_quality'] = DataProcessor.get_data_quality_info(data, attraction_type)
        return data
