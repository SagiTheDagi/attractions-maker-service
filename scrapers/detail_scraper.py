"""
Scraper for extracting detailed attraction information from Google Maps pages.
"""
import re
from typing import Optional, List, Dict, Tuple
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from utils.logger import log
from utils.hebrew_handler import (
    clean_hebrew_text,
    parse_duration_hebrew,
    extract_price_range_hebrew,
    is_closed_hebrew,
    detect_time_of_day_hebrew,
)
from config.selectors import SELECTORS, PATTERNS, HEBREW_DAYS
from config.settings import ELEMENT_WAIT_TIMEOUT, MAX_IMAGES, SCREENSHOT_ON_ERROR


class DetailScraper:
    """Extracts detailed information from a Google Maps attraction page."""

    def __init__(self, page: Page):
        self.page = page

    async def extract_all(self, url: str) -> Dict:
        """
        Extract all available data from an attraction page.

        Args:
            url: Google Maps URL of the attraction

        Returns:
            Dictionary containing extracted data
        """
        log.info(f"Extracting data from: {url}")

        data = {
            "google_maps_url": url,
        }

        # Extract coordinates from URL first (most reliable method)
        # For shortened URLs, get the actual URL after redirect
        current_url = self.page.url
        coords = self._extract_coordinates_from_url(current_url)
        if not coords:
            # Fallback: try original URL
            coords = self._extract_coordinates_from_url(url)
        if not coords:
            # Last resort: extract from page data attribute or JavaScript
            coords = await self._extract_coordinates_from_page()
        if coords:
            data["lat"], data["lng"] = coords

        # Extract basic information
        data["name"] = await self._extract_name()
        data["description"] = await self._extract_description()
        data["category"] = await self._extract_category()

        # Extract location
        data["city"] = await self._extract_city()

        # Extract price range
        price_range = await self._extract_price_range()
        if price_range:
            data["price_range"] = price_range

        # Extract hours
        hours = await self._extract_hours()
        if hours:
            data["hours"] = hours
            data["closed_days"] = self._get_closed_days(hours)

        # Extract popular times / busy days
        busy_days = await self._extract_busy_days()
        if busy_days:
            data["busy_days"] = busy_days

        # Extract recommended time
        recommended_time = await self._extract_recommended_time()
        if recommended_time:
            data["recommended_time"] = recommended_time

        # Extract duration (for activities)
        duration = await self._extract_duration()
        if duration:
            data["duration"] = duration

        # Extract dietary options (for restaurants)
        dietary = await self._extract_dietary_options()
        if dietary:
            data["dietary_options"] = dietary

        # Extract website first (for fallback)
        website = await self._extract_website()
        if website:
            data["website"] = website

        # Extract tickets/reservation link (unified)
        tickets_link = await self._extract_tickets_or_reservations_link()
        if tickets_link:
            data["tickets_link"] = tickets_link
        elif website:
            # Use website as fallback
            data["tickets_link"] = website

        # Extract tags
        tags = await self._extract_tags()
        if tags:
            data["tags"] = tags

        # Extract images
        images = await self._extract_images()
        if images:
            data["images"] = images

        log.info(f"Extracted {len(data)} fields for: {data.get('name', 'Unknown')}")
        return data

    def _extract_coordinates_from_url(self, url: str) -> Optional[Tuple[float, float]]:
        """Extract latitude and longitude from Google Maps URL."""
        try:
            match = re.search(PATTERNS["coordinates_url"], url)
            if match:
                lat = float(match.group(1))
                lng = float(match.group(2))
                log.debug(f"Extracted coordinates from URL: {lat}, {lng}")
                return (lat, lng)
        except Exception as e:
            log.warning(f"Failed to extract coordinates from URL: {e}")
        return None

    async def _extract_coordinates_from_page(self) -> Optional[Tuple[float, float]]:
        """Extract coordinates from page data or meta tags."""
        try:
            # Try to get coordinates from page URL after any redirects
            current_url = self.page.url
            match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', current_url)
            if match:
                lat = float(match.group(1))
                lng = float(match.group(2))
                log.debug(f"Extracted coordinates from page URL: {lat}, {lng}")
                return (lat, lng)

            # Try another URL format
            match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', current_url)
            if match:
                lat = float(match.group(1))
                lng = float(match.group(2))
                log.debug(f"Extracted coordinates from page URL (alt format): {lat}, {lng}")
                return (lat, lng)

            # Try to extract from meta tags or data attributes
            meta_content = await self.page.get_attribute('meta[property="og:latitude"]', 'content')
            if meta_content:
                lat = float(meta_content)
                meta_lng = await self.page.get_attribute('meta[property="og:longitude"]', 'content')
                if meta_lng:
                    lng = float(meta_lng)
                    log.debug(f"Extracted coordinates from meta tags: {lat}, {lng}")
                    return (lat, lng)

        except Exception as e:
            log.debug(f"Failed to extract coordinates from page: {e}")

        return None

    async def _extract_with_selectors(self, selector_key: str, attribute: Optional[str] = None) -> Optional[str]:
        """
        Extract text using primary and fallback selectors.

        Args:
            selector_key: Key in SELECTORS dict
            attribute: HTML attribute to extract (None for text content)

        Returns:
            Extracted text or None
        """
        selectors_config = SELECTORS.get(selector_key, {})

        # Try primary selector
        primary = selectors_config.get("primary")
        if primary:
            try:
                element = await self.page.wait_for_selector(primary, timeout=ELEMENT_WAIT_TIMEOUT, state="attached")
                if element:
                    if attribute:
                        value = await element.get_attribute(attribute)
                    else:
                        value = await element.inner_text()
                    return clean_hebrew_text(value)
            except (PlaywrightTimeout, Exception) as e:
                log.debug(f"Primary selector failed for {selector_key}: {e}")

        # Try fallback selectors
        fallbacks = selectors_config.get("fallback", [])
        for fallback_selector in fallbacks:
            try:
                element = await self.page.wait_for_selector(fallback_selector, timeout=ELEMENT_WAIT_TIMEOUT // 2, state="attached")
                if element:
                    if attribute:
                        value = await element.get_attribute(attribute)
                    else:
                        value = await element.inner_text()
                    return clean_hebrew_text(value)
            except (PlaywrightTimeout, Exception):
                continue

        return None

    async def _extract_name(self) -> Optional[str]:
        """Extract attraction name."""
        name = await self._extract_with_selectors("name")
        if name:
            log.debug(f"Extracted name: {name}")
        else:
            log.warning("Failed to extract name")
        return name

    async def _extract_description(self) -> Optional[str]:
        """Extract attraction description."""
        description = await self._extract_with_selectors("description")
        if description:
            log.debug(f"Extracted description: {description[:50]}...")
        return description

    async def _extract_category(self) -> Optional[str]:
        """Extract category/type of attraction."""
        category = await self._extract_with_selectors("category")
        if category:
            log.debug(f"Extracted category: {category}")
        return category

    async def _extract_city(self) -> Optional[str]:
        """Extract city from address."""
        address = await self._extract_with_selectors("address")
        if address:
            # Normalize city name (handle Japanese addresses)
            city = self._normalize_city(address)
            log.debug(f"Extracted city: {city}")
            return city
        return None

    def _normalize_city(self, address: str) -> str:
        """Normalize city name from address."""
        if not address:
            return address

        # Remove postal codes (Japanese format: 〒123-4567)
        address_clean = re.sub(r'〒\d{3}-?\d{4}\s*', '', address)

        # Map of cities to Hebrew names
        city_mapping = {
            'Tokyo': 'טוקיו',
            'tokyo': 'טוקיו',
            '東京': 'טוקיו',
            'Osaka': 'אוסקה',
            'osaka': 'אוסקה',
            '大阪': 'אוסקה',
            'Kyoto': 'קיוטו',
            'kyoto': 'קיוטו',
            '京都': 'קיוטו',
            'Yokohama': 'יוקוהמה',
            'yokohama': 'יוקוהמה',
            '横浜': 'יוקוהמה',
        }

        # Check for explicit city names first
        for city_name, hebrew_name in city_mapping.items():
            if city_name in address:
                return hebrew_name

        # Tokyo neighborhoods that should be normalized to Tokyo
        tokyo_areas = ['Shibuya', 'Shinjuku', 'Chiyoda', 'Minato', 'Chūō', 'Chuo',
                       'Taitō', 'Taito', 'Sumida', 'Kōtō', 'Koto', 'Shinagawa',
                       'Meguro', 'Ōta', 'Ota', 'Setagaya', 'Nakano', 'Suginami',
                       'Toshima', 'Kita', 'Arakawa', 'Itabashi', 'Nerima', 'Adachi',
                       'Katsushika', 'Edogawa']

        # Only normalize to Tokyo if it's a known Tokyo neighborhood
        for area in tokyo_areas:
            if area in address:
                return 'טוקיו'

        # Try to extract city from comma-separated parts
        parts = address_clean.split(',')
        if len(parts) >= 2:
            # Last part is usually country, second-to-last might be prefecture/city
            for i in range(len(parts) - 1, -1, -1):
                part = parts[i].strip()
                # Skip if it's too short, all digits, or looks like a country
                if len(part) > 3 and not part.isdigit() and part not in ['Japan', 'Japan']:
                    # Check if this part contains a known city
                    for city_name, hebrew_name in city_mapping.items():
                        if city_name in part:
                            return hebrew_name
                    # If not a known city but looks valid, return as-is
                    if not any(char.isdigit() for char in part):
                        return part

        # Return cleaned address if can't parse
        return address_clean.strip()

    async def _extract_price_range(self) -> Optional[str]:
        """Extract price range."""
        # Try to find price element
        price_text = await self._extract_with_selectors("price")
        if price_text:
            price_range = extract_price_range_hebrew(price_text)
            if price_range:
                log.debug(f"Extracted price range: {price_range}")
                return price_range

        # Also check in description or other text
        description = await self._extract_description()
        if description:
            price_range = extract_price_range_hebrew(description)
            if price_range:
                log.debug(f"Extracted price range from description: {price_range}")
                return price_range

        return None

    async def _extract_hours(self) -> Optional[Dict]:
        """Extract operating hours."""
        try:
            # Click to expand hours if needed
            hours_button = await self.page.query_selector(SELECTORS["hours_button"]["primary"])
            if hours_button:
                await hours_button.click()
                await self.page.wait_for_timeout(1000)

            # Get hours table or content
            hours_element = await self.page.query_selector(SELECTORS["hours_content"]["primary"])
            if not hours_element:
                return None

            # Extract hours text
            hours_text = await hours_element.inner_text()
            hours_dict = self._parse_hours_text(hours_text)

            if hours_dict:
                log.debug(f"Extracted hours: {hours_dict}")
                return hours_dict

        except Exception as e:
            log.warning(f"Failed to extract hours: {e}")

        return None

    def _parse_hours_text(self, text: str) -> Optional[Dict]:
        """Parse hours text into structured format."""
        if not text:
            return None

        # Check for 24/7 operation
        text_lower = text.lower()
        if any(indicator in text_lower for indicator in ['24/7', '24 hours', 'open 24', 'פתוח 24', 'סביב השעון']):
            # Return 24/7 hours for all days
            all_days_24_7 = {}
            for english_day in HEBREW_DAYS.values():
                # Remove duplicates by using set
                if english_day not in all_days_24_7:
                    all_days_24_7[english_day] = {
                        "open": "00:00",
                        "close": "23:59"
                    }
            return all_days_24_7

        hours_dict = {}
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if it's a day + hours line
            for hebrew_day, english_day in HEBREW_DAYS.items():
                if hebrew_day in line:
                    # Extract time
                    if is_closed_hebrew(line):
                        hours_dict[english_day] = "closed"
                    else:
                        # Try to find times (HH:MM format)
                        times = re.findall(r'(\d{1,2}):(\d{2})', line)
                        if len(times) >= 2:
                            open_time = f"{times[0][0].zfill(2)}:{times[0][1]}"
                            close_time = f"{times[1][0].zfill(2)}:{times[1][1]}"
                            hours_dict[english_day] = {
                                "open": open_time,
                                "close": close_time
                            }
                    break

        return hours_dict if hours_dict else None

    def _get_closed_days(self, hours: Dict) -> List[str]:
        """Extract closed days from hours dictionary."""
        closed_days = []
        for day, hours_info in hours.items():
            if hours_info == "closed" or (isinstance(hours_info, dict) and not hours_info):
                closed_days.append(day)
        return closed_days

    async def _extract_busy_days(self) -> Optional[List[str]]:
        """Extract busy days from popular times."""
        try:
            popular_times = await self.page.query_selector(SELECTORS["popular_times"]["primary"])
            if popular_times:
                # This is complex - popular times are shown as graphs
                # For now, we'll extract text and look for day names
                text = await popular_times.inner_text()

                busy_days = []
                for hebrew_day, english_day in HEBREW_DAYS.items():
                    if hebrew_day in text:
                        # Simple heuristic: if the day is mentioned in popular times, it's busy
                        busy_days.append(english_day)

                if busy_days:
                    log.debug(f"Extracted busy days: {busy_days}")
                    return busy_days

        except Exception as e:
            log.debug(f"Failed to extract busy days: {e}")

        # Default heuristic: weekends are usually busy
        return ["Friday", "Saturday"]

    async def _extract_recommended_time(self) -> Optional[str]:
        """Extract recommended time to visit."""
        # Check in description or category text
        description = await self._extract_description()
        if description:
            time_of_day = detect_time_of_day_hebrew(description)
            if time_of_day:
                log.debug(f"Extracted recommended time: {time_of_day}")
                return time_of_day

        # Check category
        category = await self._extract_category()
        if category:
            time_of_day = detect_time_of_day_hebrew(category)
            if time_of_day:
                return time_of_day

        return None

    async def _extract_duration(self) -> Optional[int]:
        """Extract duration for activities (in minutes)."""
        # Check in description
        description = await self._extract_description()
        if description:
            duration = parse_duration_hebrew(description)
            if duration:
                log.debug(f"Extracted duration: {duration} minutes")
                return duration

        # Check in other text elements
        try:
            page_text = await self.page.inner_text('body')
            duration = parse_duration_hebrew(page_text)
            if duration:
                log.debug(f"Extracted duration from page: {duration} minutes")
                return duration
        except Exception as e:
            log.debug(f"Failed to search page for duration: {e}")

        return None

    async def _extract_dietary_options(self) -> Optional[List[str]]:
        """Extract dietary options for restaurants."""
        dietary_options = []

        try:
            # Look for dietary/dining options section
            dietary_element = await self.page.query_selector(SELECTORS["dietary"]["primary"])
            if dietary_element:
                text = await dietary_element.inner_text()
                text_lower = text.lower()

                # Check for common dietary options
                if any(word in text_lower for word in ['vegan', 'טבעוני', 'טבעונית']):
                    dietary_options.append('vegan')
                if any(word in text_lower for word in ['vegetarian', 'צמחוני', 'צמחונית']):
                    dietary_options.append('vegetarian')
                if any(word in text_lower for word in ['kosher', 'כשר', 'כשרה']):
                    dietary_options.append('kosher')
                if any(word in text_lower for word in ['gluten-free', 'ללא גלוטן']):
                    dietary_options.append('gluten-free')
                if any(word in text_lower for word in ['halal', 'חלאל']):
                    dietary_options.append('halal')

        except Exception as e:
            log.debug(f"Failed to extract dietary options: {e}")

        if dietary_options:
            log.debug(f"Extracted dietary options: {dietary_options}")
        return dietary_options if dietary_options else None

    async def _extract_website(self) -> Optional[str]:
        """Extract website URL."""
        try:
            website_element = await self.page.query_selector(SELECTORS["website"]["primary"])
            if not website_element:
                # Try fallback
                for fallback in SELECTORS["website"]["fallback"]:
                    website_element = await self.page.query_selector(fallback)
                    if website_element:
                        break

            if website_element:
                link = await website_element.get_attribute('href')
                if link:
                    log.debug(f"Extracted website: {link}")
                    return link

        except Exception as e:
            log.debug(f"Failed to extract website: {e}")

        return None

    async def _extract_tickets_or_reservations_link(self) -> Optional[str]:
        """Extract tickets/reservation link (works for both restaurants and activities)."""
        try:
            # Try tickets first
            tickets_element = await self.page.query_selector(SELECTORS["book_tickets"]["primary"])
            if not tickets_element:
                # Try fallback
                for fallback in SELECTORS["book_tickets"]["fallback"]:
                    tickets_element = await self.page.query_selector(fallback)
                    if tickets_element:
                        break

            if tickets_element:
                link = await tickets_element.get_attribute('href')
                if link:
                    log.debug(f"Extracted tickets link: {link}")
                    return link

            # Try reservations
            reserve_element = await self.page.query_selector(SELECTORS["reserve_table"]["primary"])
            if not reserve_element:
                # Try fallback
                for fallback in SELECTORS["reserve_table"]["fallback"]:
                    reserve_element = await self.page.query_selector(fallback)
                    if reserve_element:
                        break

            if reserve_element:
                link = await reserve_element.get_attribute('href')
                if link:
                    log.debug(f"Extracted reservation link: {link}")
                    return link

        except Exception as e:
            log.debug(f"Failed to extract tickets/reservation link: {e}")

        return None

    async def _extract_tags(self) -> Optional[List[str]]:
        """Extract tags/keywords from reviews or description."""
        tags = []

        try:
            # Try to get review tags
            review_tags_element = await self.page.query_selector(SELECTORS["review_tags"]["primary"])
            if review_tags_element:
                text = await review_tags_element.inner_text()
                # Split by common separators
                tag_list = [tag.strip() for tag in re.split(r'[,•·]', text) if tag.strip()]
                tags.extend(tag_list[:10])  # Limit to 10 tags

        except Exception as e:
            log.debug(f"Failed to extract review tags: {e}")

        # Also extract from category
        category = await self._extract_category()
        if category and category not in tags:
            tags.append(category)

        if tags:
            tags = [clean_hebrew_text(tag) for tag in tags if tag]
            log.debug(f"Extracted {len(tags)} tags")
            return tags

        return None

    async def _extract_images(self) -> Optional[List[str]]:
        """Extract image URLs."""
        images = []

        try:
            # Click on photos to open gallery (if available)
            photos_button = await self.page.query_selector(SELECTORS["images_container"]["primary"])
            if photos_button:
                await photos_button.click()
                await self.page.wait_for_timeout(2000)

            # Get all image elements
            image_elements = await self.page.query_selector_all(SELECTORS["images"]["primary"])

            for img_element in image_elements[:MAX_IMAGES]:
                try:
                    src = await img_element.get_attribute('src')
                    if src and 'googleusercontent' in src:
                        # Get high-res version by modifying URL parameters
                        high_res_url = re.sub(r'=w\d+-h\d+', '=w1200-h800', src)
                        if high_res_url not in images:
                            images.append(high_res_url)
                except Exception:
                    continue

        except Exception as e:
            log.debug(f"Failed to extract images: {e}")

        if images:
            log.debug(f"Extracted {len(images)} image URLs")
        return images if images else None
