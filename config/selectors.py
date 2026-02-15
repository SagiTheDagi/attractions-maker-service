"""
CSS and XPath selectors for Google Maps elements.
Note: Google Maps frequently changes its DOM structure, so these selectors may need updates.
"""

# Main attraction information
SELECTORS = {
    # Name
    "name": {
        "primary": "h1.DUwDvf",
        "fallback": ["h1[class*='fontHeadlineLarge']", "h1.lfPIob"],
        "xpath": "//h1[contains(@class, 'DUwDvf') or contains(@class, 'fontHeadlineLarge')]"
    },

    # Description
    "description": {
        "primary": "div.WeS02d.fontBodyMedium",
        "fallback": ["div[class*='description']", "div.PYvSYb"],
        "xpath": "//div[contains(@class, 'WeS02d')]"
    },

    # Category/Type
    "category": {
        "primary": "button[jsaction*='category']",
        "fallback": ["button.DkEaL", "div[aria-label*='Category']"],
        "xpath": "//button[contains(@jsaction, 'category')]"
    },

    # Price range (₪ symbols)
    "price": {
        "primary": "span[aria-label*='Price']",
        "fallback": ["span.mgr77e", "div[aria-label*='₪']"],
        "xpath": "//span[contains(@aria-label, 'Price') or contains(text(), '₪')]"
    },

    # Rating and reviews
    "rating": {
        "primary": "div.F7nice",
        "fallback": ["span.ceNzKf", "div[aria-label*='stars']"],
        "xpath": "//div[contains(@class, 'F7nice')]"
    },

    # Address
    "address": {
        "primary": "button[data-item-id='address']",
        "fallback": ["div[aria-label*='Address']", "button.CsEnBe[aria-label]"],
        "xpath": "//button[@data-item-id='address']"
    },

    # Hours button (to expand hours)
    "hours_button": {
        "primary": "button[data-item-id*='hours']",
        "fallback": ["button[aria-label*='Hours']", "div.t39EBf button"],
        "xpath": "//button[contains(@data-item-id, 'hours') or contains(@aria-label, 'Hours')]"
    },

    # Hours content (after expanding)
    "hours_content": {
        "primary": "table.eK4R0e",
        "fallback": ["div[aria-label*='Hours']", "table.WgFkxc"],
        "xpath": "//table[contains(@class, 'eK4R0e')]"
    },

    # Individual hour rows
    "hour_rows": {
        "primary": "tr",
        "fallback": ["div[role='row']"],
        "xpath": ".//tr"
    },

    # Popular times
    "popular_times": {
        "primary": "div[aria-label*='Popular times']",
        "fallback": ["div.section-popular-times", "div[class*='popular']"],
        "xpath": "//div[contains(@aria-label, 'Popular times')]"
    },

    # Images container
    "images_container": {
        "primary": "button[aria-label*='Photos']",
        "fallback": ["button.aoRNLd", "div[aria-label*='Photo']"],
        "xpath": "//button[contains(@aria-label, 'Photos') or contains(@aria-label, 'Photo')]"
    },

    # Image elements
    "images": {
        "primary": "img[src*='googleusercontent']",
        "fallback": ["img.U39Pmb", "img[class*='photo']"],
        "xpath": "//img[contains(@src, 'googleusercontent')]"
    },

    # Website link
    "website": {
        "primary": "a[data-item-id='authority']",
        "fallback": ["a[aria-label*='Website']", "a.CsEnBe[href^='http']"],
        "xpath": "//a[@data-item-id='authority']"
    },

    # Phone number
    "phone": {
        "primary": "button[data-item-id*='phone']",
        "fallback": ["button[aria-label*='Phone']", "button.CsEnBe[aria-label*='Call']"],
        "xpath": "//button[contains(@data-item-id, 'phone')]"
    },

    # Plus code / Coordinates
    "plus_code": {
        "primary": "button[data-item-id='oloc']",
        "fallback": ["div[aria-label*='Plus code']", "button[data-tooltip*='Plus code']"],
        "xpath": "//button[@data-item-id='oloc']"
    },

    # Accessibility info
    "accessibility": {
        "primary": "div[aria-label*='Accessibility']",
        "fallback": ["div[class*='accessibility']"],
        "xpath": "//div[contains(@aria-label, 'Accessibility')]"
    },

    # Amenities
    "amenities": {
        "primary": "div[aria-label*='Amenities']",
        "fallback": ["div.iP2t7d", "div[class*='amenities']"],
        "xpath": "//div[contains(@aria-label, 'Amenities')]"
    },

    # Review tags/keywords
    "review_tags": {
        "primary": "div[jsaction*='pane.reviewChart.moreDescription']",
        "fallback": ["button.hh2c6", "div[class*='review-tag']"],
        "xpath": "//div[contains(@jsaction, 'reviewChart')]"
    },

    # Search results list
    "search_results": {
        "primary": "div[role='feed']",
        "fallback": ["div.m6QErb", "div[aria-label*='Results']"],
        "xpath": "//div[@role='feed']"
    },

    # Individual search result item
    "search_result_item": {
        "primary": "a[href*='/maps/place/']",
        "fallback": ["a.hfpxzc", "a[aria-label]"],
        "xpath": "//a[contains(@href, '/maps/place/')]"
    },

    # Load more button in search
    "load_more": {
        "primary": "button[aria-label*='More results']",
        "fallback": ["button.HlvSq", "button[class*='load-more']"],
        "xpath": "//button[contains(@aria-label, 'More results')]"
    },

    # Reserve a table button (restaurants)
    "reserve_table": {
        "primary": "a[data-item-id='reservations']",
        "fallback": ["a[aria-label*='Reserve']", "a[href*='reservation']"],
        "xpath": "//a[@data-item-id='reservations' or contains(@aria-label, 'Reserve')]"
    },

    # Book tickets button (activities)
    "book_tickets": {
        "primary": "a[data-item-id='tickets']",
        "fallback": ["a[aria-label*='Tickets']", "a[href*='ticket']"],
        "xpath": "//a[@data-item-id='tickets' or contains(@aria-label, 'Tickets')]"
    },

    # Menu link (restaurants)
    "menu": {
        "primary": "button[aria-label*='Menu']",
        "fallback": ["a[data-item-id='menu']", "button[data-tab-index*='menu']"],
        "xpath": "//button[contains(@aria-label, 'Menu')]"
    },

    # Dietary options/tags (restaurants)
    "dietary": {
        "primary": "div[aria-label*='Dining options']",
        "fallback": ["div[class*='dietary']", "span[aria-label*='Vegetarian']"],
        "xpath": "//div[contains(@aria-label, 'Dining options')]"
    },
}

# Regex patterns for data extraction
PATTERNS = {
    # Extract coordinates from URL: /@32.0877788,34.7803984,15z
    "coordinates_url": r"/@(-?\d+\.\d+),(-?\d+\.\d+),(\d+)z",

    # Extract place ID from URL
    "place_id": r"/place/([^/]+)/@",

    # Extract price symbols (₪₪₪ or $$$)
    "price_symbols": r"[₪$]{1,4}",

    # Extract duration from text (e.g., "2-3 hours", "90 minutes")
    "duration_hours": r"(\d+)(?:-(\d+))?\s*(?:שעות|hours?)",
    "duration_minutes": r"(\d+)(?:-(\d+))?\s*(?:דקות|minutes?)",

    # Extract time from hours text (e.g., "08:00", "8:00 AM")
    "time_24h": r"(\d{1,2}):(\d{2})",
    "time_12h": r"(\d{1,2}):(\d{2})\s*(AM|PM)",

    # Extract ratings (e.g., "4.5 stars")
    "rating": r"(\d+\.?\d*)\s*(?:stars?|כוכבים)",

    # Extract review count (e.g., "1,234 reviews")
    "reviews": r"([\d,]+)\s*(?:reviews?|ביקורות)",
}

# Hebrew day names mapping
HEBREW_DAYS = {
    "ראשון": "Sunday",
    "שני": "Monday",
    "שלישי": "Tuesday",
    "רביעי": "Wednesday",
    "חמישי": "Thursday",
    "שישי": "Friday",
    "שבת": "Saturday",
    "יום א'": "Sunday",
    "יום ב'": "Monday",
    "יום ג'": "Tuesday",
    "יום ד'": "Wednesday",
    "יום ה'": "Thursday",
    "יום ו'": "Friday",
    "שבת": "Saturday",
}

# English to Hebrew day names (for search queries)
ENGLISH_TO_HEBREW_DAYS = {
    "Sunday": "ראשון",
    "Monday": "שני",
    "Tuesday": "שלישי",
    "Wednesday": "רביעי",
    "Thursday": "חמישי",
    "Friday": "שישי",
    "Saturday": "שבת",
}
