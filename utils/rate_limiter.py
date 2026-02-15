"""
Rate limiting utilities to avoid bot detection.
"""
import asyncio
import random
from utils.logger import log
from config.settings import (
    BASE_DELAY_MIN,
    BASE_DELAY_MAX,
    LONG_PAUSE_INTERVAL,
    LONG_PAUSE_MIN,
    LONG_PAUSE_MAX,
)


class RateLimiter:
    """Manages request rate limiting with adaptive delays."""

    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.delay_multiplier = 1.0

    async def wait(self):
        """Apply delay before next request (non-blocking)."""
        self.request_count += 1

        # Determine if we need a long pause
        if self.request_count % LONG_PAUSE_INTERVAL == 0:
            delay = random.uniform(LONG_PAUSE_MIN, LONG_PAUSE_MAX)
            log.info(f"Long pause after {self.request_count} requests: {delay:.1f}s")
        else:
            # Normal delay with multiplier for adaptive rate limiting
            base_delay = random.uniform(BASE_DELAY_MIN, BASE_DELAY_MAX)
            delay = base_delay * self.delay_multiplier

        log.debug(f"Waiting {delay:.2f}s before next request (multiplier: {self.delay_multiplier:.2f}x)")
        await asyncio.sleep(delay)

    def on_error(self):
        """Increase delay on errors (adaptive)."""
        self.error_count += 1
        # Increase multiplier by 50% on each error, max 5x
        self.delay_multiplier = min(self.delay_multiplier * 1.5, 5.0)
        log.warning(f"Error detected. Increasing delay multiplier to {self.delay_multiplier:.2f}x")

    def on_success(self):
        """Gradually decrease delay on success."""
        # Slowly decrease multiplier back to 1.0
        if self.delay_multiplier > 1.0:
            self.delay_multiplier = max(self.delay_multiplier * 0.9, 1.0)
            log.debug(f"Success. Decreasing delay multiplier to {self.delay_multiplier:.2f}x")

    def reset(self):
        """Reset the rate limiter state."""
        self.request_count = 0
        self.error_count = 0
        self.delay_multiplier = 1.0
        log.info("Rate limiter reset")

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "total_requests": self.request_count,
            "errors": self.error_count,
            "delay_multiplier": self.delay_multiplier,
            "error_rate": self.error_count / max(self.request_count, 1),
        }
