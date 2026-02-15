"""
Scraper for discovering attractions by searching Google Maps.
"""
import urllib.parse
from typing import List, Dict
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from utils.logger import log
from config.selectors import SELECTORS
from config.settings import GOOGLE_MAPS_SEARCH_URL, MAX_SEARCH_RESULTS, ELEMENT_WAIT_TIMEOUT


class SearchScraper:
    """Searches Google Maps and extracts URLs of attractions."""

    def __init__(self, page: Page):
        self.page = page

    async def search_attractions(self, city: str, attraction_type: str) -> List[str]:
        """
        Search for attractions in a city and return their URLs.

        Args:
            city: City name (in Hebrew or English)
            attraction_type: Type of attraction to search for (e.g., "restaurants", "activities")

        Returns:
            List of Google Maps URLs
        """
        query = f"{attraction_type} in {city}"
        log.info(f"Searching for: {query}")

        # Build search URL
        encoded_query = urllib.parse.quote(query)
        search_url = f"{GOOGLE_MAPS_SEARCH_URL}{encoded_query}"

        # Navigate to search page
        try:
            await self.page.goto(search_url, wait_until="networkidle", timeout=30000)
            await self.page.wait_for_timeout(2000)
        except Exception as e:
            log.error(f"Failed to navigate to search page: {e}")
            return []

        # Wait for results to load
        try:
            await self.page.wait_for_selector(SELECTORS["search_results"]["primary"], timeout=ELEMENT_WAIT_TIMEOUT)
        except PlaywrightTimeout:
            log.warning("Search results not found")
            return []

        # Scroll to load more results
        await self._scroll_results()

        # Extract attraction URLs
        urls = await self._extract_urls()

        log.info(f"Found {len(urls)} attractions for query: {query}")
        return urls[:MAX_SEARCH_RESULTS]

    async def _scroll_results(self):
        """Scroll through search results to load more items."""
        try:
            # Get the scrollable results container
            results_container = await self.page.query_selector(SELECTORS["search_results"]["primary"])

            if results_container:
                # Scroll multiple times to load more results
                for _ in range(5):  # Scroll 5 times
                    await results_container.evaluate("el => el.scrollBy(0, el.scrollHeight)")
                    await self.page.wait_for_timeout(1000)

                log.debug("Scrolled through search results")

        except Exception as e:
            log.warning(f"Failed to scroll results: {e}")

    async def _extract_urls(self) -> List[str]:
        """Extract Google Maps URLs from search results."""
        urls = []

        try:
            # Find all result items
            result_elements = await self.page.query_selector_all(SELECTORS["search_result_item"]["primary"])

            for element in result_elements:
                try:
                    href = await element.get_attribute('href')
                    if href and '/maps/place/' in href:
                        # Clean up the URL (remove unnecessary parameters)
                        clean_url = href.split('?')[0] if '?' in href else href
                        if clean_url not in urls:
                            urls.append(clean_url)
                except Exception:
                    continue

        except Exception as e:
            log.error(f"Failed to extract URLs from search results: {e}")

        return urls

    async def search_by_config(self, search_config: Dict) -> Dict[str, List[str]]:
        """
        Search for attractions based on configuration.

        Args:
            search_config: Dictionary with 'cities' and 'types' lists

        Returns:
            Dictionary mapping search queries to lists of URLs
        """
        results = {}

        cities = search_config.get('cities', [])
        types = search_config.get('types', [])

        for city in cities:
            for attr_type in types:
                query_key = f"{city}_{attr_type}"
                urls = await self.search_attractions(city, attr_type)
                results[query_key] = urls

                # Add delay between searches
                await self.page.wait_for_timeout(3000)

        return results
