"""
Browser manager with anti-detection measures for Playwright.
"""
import random
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from fake_useragent import UserAgent
from utils.logger import log
from config.settings import (
    HEADLESS,
    VIEWPORT_WIDTH,
    VIEWPORT_HEIGHT,
    LOCALE,
    TIMEZONE,
    ACCEPT_LANGUAGE,
    USER_AGENTS,
    PAGE_LOAD_TIMEOUT,
)


class BrowserManager:
    """Manages browser instances with anti-detection configuration."""

    def __init__(self, headless: bool = HEADLESS):
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.ua_generator = UserAgent()

    async def start(self):
        """Start the browser with anti-detection measures."""
        log.info("Starting browser...")

        self.playwright = await async_playwright().start()

        # Launch browser with anti-detection settings
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )

        # Create browser context with stealth settings
        await self._create_context()

        log.info(f"Browser started (headless={self.headless})")

    async def _create_context(self):
        """Create a new browser context with anti-detection configuration."""
        # Random viewport size (slight variation)
        viewport_width = VIEWPORT_WIDTH + random.randint(-50, 50)
        viewport_height = VIEWPORT_HEIGHT + random.randint(-50, 50)

        # Random user agent
        user_agent = random.choice(USER_AGENTS)

        log.debug(f"Creating context with viewport {viewport_width}x{viewport_height}")

        self.context = await self.browser.new_context(
            viewport={'width': viewport_width, 'height': viewport_height},
            locale=LOCALE,
            timezone_id=TIMEZONE,
            user_agent=user_agent,
            accept_downloads=False,
            java_script_enabled=True,
            extra_http_headers={
                'Accept-Language': ACCEPT_LANGUAGE,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )

        # Add stealth JavaScript to remove webdriver detection
        await self.context.add_init_script("""
            // Remove webdriver flag
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['he-IL', 'he', 'en-US', 'en']
            });

            // Mock platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            // Mock chrome object
            window.chrome = {
                runtime: {}
            };

            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        # Create new page
        self.page = await self.context.new_page()
        self.page.set_default_timeout(PAGE_LOAD_TIMEOUT)

        log.debug("Browser context created with stealth configuration")

    async def new_page(self) -> Page:
        """Create a new page in the current context."""
        if not self.context:
            await self.start()

        page = await self.context.new_page()
        page.set_default_timeout(PAGE_LOAD_TIMEOUT)
        return page

    async def navigate(self, url: str, wait_until: str = "networkidle") -> bool:
        """
        Navigate to a URL with error handling.

        Args:
            url: URL to navigate to
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')

        Returns:
            True if navigation successful, False otherwise
        """
        try:
            log.info(f"Navigating to: {url}")
            await self.page.goto(url, wait_until=wait_until, timeout=PAGE_LOAD_TIMEOUT)

            # Random scroll to simulate human behavior
            await self._simulate_human_scroll()

            return True
        except Exception as e:
            log.error(f"Navigation failed: {e}")
            return False

    async def _simulate_human_scroll(self):
        """Simulate human-like scrolling behavior."""
        try:
            # Random small scroll
            scroll_amount = random.randint(100, 500)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await self.page.wait_for_timeout(random.randint(500, 1500))

            # Scroll back up a bit
            scroll_back = random.randint(50, 200)
            await self.page.evaluate(f"window.scrollBy(0, -{scroll_back})")
            await self.page.wait_for_timeout(random.randint(300, 800))

            log.debug("Simulated human scroll behavior")
        except Exception as e:
            log.warning(f"Failed to simulate scroll: {e}")

    async def random_mouse_movement(self):
        """Simulate random mouse movements."""
        try:
            # Move mouse to random positions
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, VIEWPORT_WIDTH - 100)
                y = random.randint(100, VIEWPORT_HEIGHT - 100)
                await self.page.mouse.move(x, y)
                await self.page.wait_for_timeout(random.randint(100, 300))

            log.debug("Simulated mouse movements")
        except Exception as e:
            log.warning(f"Failed to simulate mouse movement: {e}")

    async def screenshot(self, filepath: str):
        """Take a screenshot of the current page."""
        try:
            await self.page.screenshot(path=filepath, full_page=True)
            log.info(f"Screenshot saved to: {filepath}")
        except Exception as e:
            log.error(f"Failed to take screenshot: {e}")

    async def restart_context(self):
        """Restart the browser context (useful after many requests)."""
        log.info("Restarting browser context...")

        if self.context:
            await self.context.close()

        await self._create_context()

        log.info("Browser context restarted")

    async def close(self):
        """Close the browser and cleanup."""
        log.info("Closing browser...")

        if self.page:
            await self.page.close()

        if self.context:
            await self.context.close()

        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()

        log.info("Browser closed")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
