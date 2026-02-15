"""
Pydantic models for attraction data with type-specific field requirements.
"""
from typing import Optional, List, Dict, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from .enums import AttractionType, PriceRange


class HoursInfo(BaseModel):
    """Operating hours for a single day."""
    open: Optional[str] = None  # Format: "HH:MM"
    close: Optional[str] = None  # Format: "HH:MM"


class BaseAttraction(BaseModel):
    """Base model with fields common to all attraction types."""
    name: str = Field(..., description="Name of the attraction")
    description: Optional[str] = Field(None, description="Description of the attraction")
    type: AttractionType = Field(..., description="Type of attraction")
    city: Optional[str] = Field(None, description="City where the attraction is located")
    google_maps_url: Optional[str] = Field(None, description="Google Maps URL")
    lat: Optional[float] = Field(None, description="Latitude coordinate")
    lng: Optional[float] = Field(None, description="Longitude coordinate")
    tags: List[str] = Field(default_factory=list, description="Tags associated with the attraction")
    busy_days: List[str] = Field(default_factory=list, description="Days when the attraction is busy")
    closed_days: List[str] = Field(default_factory=list, description="Days when the attraction is closed")
    recommended_time: Optional[str] = Field(None, description="Recommended time to visit (e.g., 'morning', 'lunch', 'evening')")
    hours: Optional[Dict[str, Union[HoursInfo, str]]] = Field(None, description="Operating hours by day of week")
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    website: Optional[str] = Field(None, description="Official website URL")
    tickets_link: Optional[str] = Field(None, description="URL to purchase tickets or make reservations")

    class Config:
        use_enum_values = True


class ActivityAttraction(BaseAttraction):
    """Model for activity-type attractions."""
    type: AttractionType = Field(default=AttractionType.ACTIVITY, frozen=True)
    category: Optional[str] = Field(None, description="Category of the activity")
    price_range: Optional[PriceRange] = Field(None, description="Price range for the activity")
    duration: Optional[int] = Field(None, description="Duration in minutes")

    # These fields should NOT be present for activities
    dietary_options: None = None


class RestaurantAttraction(BaseAttraction):
    """Model for restaurant-type attractions."""
    type: AttractionType = Field(default=AttractionType.RESTAURANT, frozen=True)
    category: Optional[str] = Field(None, description="Type of food/cuisine")
    price_range: Optional[PriceRange] = Field(None, description="Price range for the restaurant")
    dietary_options: List[str] = Field(default_factory=list, description="Dietary options (e.g., vegan, vegetarian, kosher)")

    # These fields should NOT be present for restaurants
    duration: None = None


class MallAttraction(BaseAttraction):
    """Model for mall-type attractions."""
    type: AttractionType = Field(default=AttractionType.MALL, frozen=True)
    category: Optional[str] = Field(None, description="Category of the mall")

    # These fields should NOT be present for malls
    price_range: None = None
    duration: None = None
    dietary_options: None = None


class StoreChainAttraction(BaseAttraction):
    """Model for store chain-type attractions."""
    type: AttractionType = Field(default=AttractionType.STORE_CHAIN, frozen=True)
    category: Optional[str] = Field(None, description="Category of the store")
    price_range: Optional[PriceRange] = Field(None, description="Price range for the store")

    # These fields should NOT be present for store chains
    duration: None = None
    dietary_options: None = None


# Type mapping for dynamic model selection
ATTRACTION_MODELS = {
    AttractionType.ACTIVITY: ActivityAttraction,
    AttractionType.RESTAURANT: RestaurantAttraction,
    AttractionType.MALL: MallAttraction,
    AttractionType.STORE_CHAIN: StoreChainAttraction,
}


def create_attraction(data: dict) -> BaseAttraction:
    """
    Factory function to create the appropriate attraction model based on type.

    Args:
        data: Dictionary containing attraction data including 'type' field

    Returns:
        An instance of the appropriate attraction model

    Raises:
        ValueError: If attraction type is invalid or missing
    """
    attraction_type = data.get('type')
    if not attraction_type:
        raise ValueError("Attraction type is required")

    if isinstance(attraction_type, str):
        try:
            attraction_type = AttractionType(attraction_type)
        except ValueError:
            raise ValueError(f"Invalid attraction type: {attraction_type}")

    model_class = ATTRACTION_MODELS.get(attraction_type)
    if not model_class:
        raise ValueError(f"No model found for attraction type: {attraction_type}")

    return model_class(**data)


class AttractionData(BaseModel):
    """Container for scraped attractions data with metadata."""
    metadata: Dict = Field(default_factory=dict, description="Metadata about the scraping session")
    attractions: Dict[str, List[BaseAttraction]] = Field(
        default_factory=lambda: {
            "restaurants": [],
            "activities": [],
            "malls": [],
            "store_chains": []
        },
        description="Attractions grouped by type"
    )
    failed_attractions: List[Dict] = Field(default_factory=list, description="Failed attraction attempts")

    def add_attraction(self, attraction: BaseAttraction):
        """Add an attraction to the appropriate category."""
        if isinstance(attraction, RestaurantAttraction):
            self.attractions["restaurants"].append(attraction)
        elif isinstance(attraction, ActivityAttraction):
            self.attractions["activities"].append(attraction)
        elif isinstance(attraction, MallAttraction):
            self.attractions["malls"].append(attraction)
        elif isinstance(attraction, StoreChainAttraction):
            self.attractions["store_chains"].append(attraction)

    def add_failed(self, input_data: str, error: str):
        """Add a failed attraction attempt."""
        self.failed_attractions.append({
            "input": input_data,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    def get_stats(self) -> Dict:
        """Get statistics about the scraping session."""
        total_successful = sum(len(attractions) for attractions in self.attractions.values())
        return {
            "total_attractions": total_successful + len(self.failed_attractions),
            "successful": total_successful,
            "failed": len(self.failed_attractions),
            "by_type": {
                "restaurants": len(self.attractions["restaurants"]),
                "activities": len(self.attractions["activities"]),
                "malls": len(self.attractions["malls"]),
                "store_chains": len(self.attractions["store_chains"]),
            }
        }
