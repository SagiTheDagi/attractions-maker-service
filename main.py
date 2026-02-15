"""
Main entry point for the Google Maps attractions scraper.
"""
import asyncio
import argparse
import sys
from pathlib import Path
from tqdm import tqdm
from utils.logger import log
from utils.browser_manager import BrowserManager
from utils.rate_limiter import RateLimiter
from scrapers.detail_scraper import DetailScraper
from scrapers.search_scraper import SearchScraper
from processors.input_processor import InputProcessor
from processors.output_processor import OutputProcessor
from processors.data_processor import DataProcessor
from models.enums import AttractionType
from config.settings import SCREENSHOT_ON_ERROR, OUTPUT_DIR


class AttractionsScraper:
    """Main scraper orchestration class."""

    def __init__(self, input_file: str, output_file: str = None, mode: str = "manual"):
        self.input_file = input_file
        self.output_file = output_file
        self.mode = mode

        self.browser_manager = None
        self.rate_limiter = RateLimiter()
        self.input_processor = InputProcessor()
        self.output_processor = OutputProcessor(output_file)
        self.data_processor = DataProcessor()

        self.urls_queue = []
        self.search_queue = []

    async def run(self):
        """Main execution flow."""
        log.info("Starting Google Maps attractions scraper...")

        # Process input file
        self._load_input()

        if not self.urls_queue and not self.search_queue:
            log.error("No attractions to scrape. Check your input file.")
            return

        # Start browser
        self.browser_manager = BrowserManager()
        await self.browser_manager.start()

        try:
            # Process search queries if in auto mode
            if self.search_queue:
                await self._process_search_queue()

            # Process URLs
            if self.urls_queue:
                await self._process_url_queue()

            # Finalize output
            output_path = self.output_processor.finalize()
            if output_path:
                log.info(f"✅ Scraping complete! Output saved to: {output_path}")

                # Write error log if there are failures
                if self.output_processor.data.failed_attractions:
                    self.output_processor.write_error_log()

                # Print summary
                self._print_summary()

        finally:
            # Close browser
            await self.browser_manager.close()

    def _load_input(self):
        """Load and process input file."""
        log.info(f"Loading input from: {self.input_file}")

        urls, search_items = self.input_processor.process_file(self.input_file)

        # Add URLs to queue
        self.urls_queue.extend(urls)

        # Process search items
        if search_items:
            # Convert search items to URLs (search Google Maps for each)
            self.search_queue.extend(search_items)

        log.info(f"Loaded {len(self.urls_queue)} URLs and {len(self.search_queue)} search items")

    async def _process_search_queue(self):
        """Process search queue to find attraction URLs."""
        log.info(f"Processing {len(self.search_queue)} search items...")

        search_scraper = SearchScraper(self.browser_manager.page)

        for search_item in tqdm(self.search_queue, desc="Searching attractions"):
            try:
                name = search_item.get('name', '')
                city = search_item.get('city', '')

                # Search for the attraction
                search_query = f"{name}, {city}" if city else name
                urls = await search_scraper.search_attractions(city, name)

                if urls:
                    # Take the first result (most relevant)
                    self.urls_queue.append(urls[0])
                    log.info(f"Found URL for '{search_query}': {urls[0]}")
                else:
                    log.warning(f"No results found for: {search_query}")
                    self.output_processor.add_failed_attraction(search_query, "Not found in search")

                # Rate limiting
                await self.rate_limiter.wait()

            except Exception as e:
                log.error(f"Search failed for {search_item}: {e}")
                self.output_processor.add_failed_attraction(str(search_item), str(e))

    async def _process_url_queue(self):
        """Process URL queue to scrape attraction data."""
        log.info(f"Processing {len(self.urls_queue)} URLs...")

        # Get already processed URLs from checkpoint
        processed_urls = self.output_processor.get_processed_urls()

        # Filter out already processed URLs
        urls_to_process = [url for url in self.urls_queue if url not in processed_urls]

        log.info(f"Skipping {len(self.urls_queue) - len(urls_to_process)} already processed URLs")

        detail_scraper = DetailScraper(self.browser_manager.page)

        for url in tqdm(urls_to_process, desc="Scraping attractions"):
            try:
                # Navigate to attraction page
                success = await self.browser_manager.navigate(url)

                if not success:
                    self.output_processor.add_failed_attraction(url, "Navigation failed")
                    self.rate_limiter.on_error()
                    continue

                # Extract all data
                data = await detail_scraper.extract_all(url)

                # Clean data
                data = self.data_processor.clean_data(data)

                # Infer attraction type if not provided
                if 'type' not in data:
                    inferred_type = self.data_processor.infer_attraction_type(
                        data.get('category'),
                        url
                    )
                    if inferred_type:
                        data['type'] = inferred_type.value

                # Add data quality info
                if 'type' in data:
                    attraction_type = AttractionType(data['type'])
                    data = self.data_processor.add_data_quality_info(data, attraction_type)

                # Add to output
                self.output_processor.add_attraction(data)

                # Rate limiting
                await self.rate_limiter.wait()
                self.rate_limiter.on_success()

                # Restart browser context periodically (every 20 requests)
                if self.rate_limiter.request_count % 20 == 0:
                    log.info("Restarting browser context...")
                    await self.browser_manager.restart_context()
                    detail_scraper = DetailScraper(self.browser_manager.page)

            except Exception as e:
                log.error(f"Failed to scrape {url}: {e}")

                # Take screenshot on error
                if SCREENSHOT_ON_ERROR:
                    screenshot_path = OUTPUT_DIR / f"error_{self.rate_limiter.request_count}.png"
                    await self.browser_manager.screenshot(str(screenshot_path))

                self.output_processor.add_failed_attraction(url, str(e))
                self.rate_limiter.on_error()

    def _print_summary(self):
        """Print scraping summary statistics."""
        stats = self.output_processor.get_stats()

        print("\n" + "="*50)
        print("SCRAPING SUMMARY")
        print("="*50)
        print(f"Total attractions: {stats['total_attractions']}")
        print(f"✅ Successful: {stats['successful']}")
        print(f"❌ Failed: {stats['failed']}")
        print("\nBy type:")
        for attr_type, count in stats['by_type'].items():
            print(f"  - {attr_type}: {count}")
        print("\nRate limiter stats:")
        rate_stats = self.rate_limiter.get_stats()
        print(f"  - Total requests: {rate_stats['total_requests']}")
        print(f"  - Errors: {rate_stats['errors']}")
        print(f"  - Error rate: {rate_stats['error_rate']:.2%}")
        print("="*50 + "\n")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Google Maps Attractions Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape from a CSV file with attraction names
  python main.py input/attractions.csv

  # Scrape from a text file with URLs
  python main.py input/urls.txt -o my_output.json

  # Use automatic search mode with JSON config
  python main.py input/search_config.json --mode auto
        """
    )

    parser.add_argument(
        'input_file',
        help='Input file (CSV, TXT, or JSON)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output JSON filename (default: auto-generated with timestamp)',
        default=None
    )

    parser.add_argument(
        '-m', '--mode',
        choices=['manual', 'auto', 'both'],
        default='manual',
        help='Scraping mode: manual (URLs only), auto (search), or both (default: manual)'
    )

    args = parser.parse_args()

    # Validate input file exists
    if not Path(args.input_file).exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)

    # Create and run scraper
    scraper = AttractionsScraper(
        input_file=args.input_file,
        output_file=args.output,
        mode=args.mode
    )

    # Run async main
    try:
        asyncio.run(scraper.run())
    except KeyboardInterrupt:
        log.warning("Scraping interrupted by user")
        print("\n⚠️  Scraping interrupted. Progress has been saved to checkpoint file.")
    except Exception as e:
        log.error(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
