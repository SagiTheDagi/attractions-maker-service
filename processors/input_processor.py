"""
Process input files to generate attraction processing queue.
"""
import csv
import json
from pathlib import Path
from typing import List, Dict, Tuple
from utils.logger import log
from models.enums import AttractionType


class InputProcessor:
    """Processes input files and generates attraction queue."""

    def process_file(self, filepath: str) -> Tuple[List[str], List[Dict]]:
        """
        Process input file and return URLs and search configs.

        Args:
            filepath: Path to input file

        Returns:
            Tuple of (urls_list, search_configs_list)
        """
        filepath = Path(filepath)

        if not filepath.exists():
            log.error(f"Input file not found: {filepath}")
            return [], []

        log.info(f"Processing input file: {filepath}")

        # Determine file type and process accordingly
        if filepath.suffix.lower() == '.csv':
            return self._process_csv(filepath)
        elif filepath.suffix.lower() == '.txt':
            return self._process_txt(filepath)
        elif filepath.suffix.lower() == '.json':
            return self._process_json(filepath)
        else:
            log.error(f"Unsupported file type: {filepath.suffix}")
            return [], []

    def _process_csv(self, filepath: Path) -> Tuple[List[str], List[Dict]]:
        """Process CSV file with attraction names and types."""
        urls = []
        search_items = []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    name = row.get('name', '').strip()
                    city = row.get('city', '').strip()
                    attr_type = row.get('type', '').strip()

                    if not name:
                        continue

                    # Check if it's a URL
                    if name.startswith('http'):
                        urls.append(name)
                    else:
                        # It's a name, we'll need to search for it
                        search_items.append({
                            'name': name,
                            'city': city,
                            'type': attr_type
                        })

            log.info(f"Loaded {len(urls)} URLs and {len(search_items)} search items from CSV")

        except Exception as e:
            log.error(f"Failed to process CSV file: {e}")

        return urls, search_items

    def _process_txt(self, filepath: Path) -> Tuple[List[str], List[Dict]]:
        """Process text file with URLs (one per line)."""
        urls = []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue

                    # Validate URL (accept both full and shortened Google Maps URLs)
                    if 'google.com/maps' in line or 'maps.app.goo.gl' in line:
                        urls.append(line)
                    else:
                        log.warning(f"Invalid URL in text file: {line}")

            log.info(f"Loaded {len(urls)} URLs from text file")

        except Exception as e:
            log.error(f"Failed to process text file: {e}")

        return urls, []

    def _process_json(self, filepath: Path) -> Tuple[List[str], List[Dict]]:
        """Process JSON file with search configuration."""
        urls = []
        search_configs = []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check for URLs list
            if 'urls' in data:
                urls = data['urls']

            # Check for search configuration
            if 'search_config' in data:
                search_configs.append(data['search_config'])

            # Check for manual attractions list
            if 'attractions' in data:
                for attr in data['attractions']:
                    name = attr.get('name')
                    city = attr.get('city')
                    attr_type = attr.get('type')

                    if name:
                        search_configs.append({
                            'name': name,
                            'city': city,
                            'type': attr_type
                        })

            log.info(f"Loaded {len(urls)} URLs and {len(search_configs)} search configs from JSON")

        except Exception as e:
            log.error(f"Failed to process JSON file: {e}")

        return urls, search_configs

    def validate_url(self, url: str) -> bool:
        """Validate if URL is a valid Google Maps URL."""
        return 'google.com/maps' in url and ('/place/' in url or '/search/' in url)

    def build_search_url(self, name: str, city: str = "") -> str:
        """Build a Google Maps search URL from attraction name and city."""
        import urllib.parse

        query = name
        if city:
            query = f"{name}, {city}"

        encoded_query = urllib.parse.quote(query)
        return f"https://www.google.com/maps/search/{encoded_query}"
