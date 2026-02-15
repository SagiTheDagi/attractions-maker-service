"""
Configuration settings for the Google Maps scraper.
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Google Maps settings
GOOGLE_MAPS_BASE_URL = "https://www.google.com/maps"
GOOGLE_MAPS_SEARCH_URL = "https://www.google.com/maps/search/"

# Browser settings
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
LOCALE = "he-IL"
TIMEZONE = "Asia/Jerusalem"

# Rate limiting settings
BASE_DELAY_MIN = 2.0  # Minimum delay between requests (seconds)
BASE_DELAY_MAX = 5.0  # Maximum delay between requests (seconds)
LONG_PAUSE_INTERVAL = 10  # Make a long pause every N requests
LONG_PAUSE_MIN = 13  # Minimum long pause duration (seconds)
LONG_PAUSE_MAX = 27  # Maximum long pause duration (seconds)

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # Initial retry delay (seconds)
RETRY_MULTIPLIER = 2  # Exponential backoff multiplier

# Timeout settings
PAGE_LOAD_TIMEOUT = 30000  # Page load timeout (milliseconds)
ELEMENT_WAIT_TIMEOUT = 10000  # Element wait timeout (milliseconds)
NETWORK_IDLE_TIMEOUT = 5000  # Network idle timeout (milliseconds)

# Scraping settings
MAX_IMAGES = 10  # Maximum number of images to extract
MAX_SEARCH_RESULTS = 20  # Maximum search results to process per query
SCREENSHOT_ON_ERROR = True  # Capture screenshot on errors

# Output settings
OUTPUT_FORMAT = "json"
CHECKPOINT_ENABLED = True  # Enable checkpoint saving
CHECKPOINT_INTERVAL = 1  # Save checkpoint after every N attractions

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
LOG_FILE = LOGS_DIR / "scraper.log"
LOG_ROTATION = "10 MB"
LOG_RETENTION = "1 week"

# User agent settings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

# Hebrew language settings
ACCEPT_LANGUAGE = "he-IL,he;q=0.9,en;q=0.8"
HEBREW_KEYWORDS = {
    "free": ["חינם", "ללא תשלום", "בחינם"],
    "hours": ["שעות", "שעה"],
    "minutes": ["דקות", "דקה"],
    "closed": ["סגור", "סגורה"],
    "open": ["פתוח", "פתוחה"],
}

# Data quality thresholds
MIN_NAME_LENGTH = 2
MIN_DESCRIPTION_LENGTH = 10
MIN_COMPLETENESS_SCORE = 0.5  # Minimum completeness score (0-1)
