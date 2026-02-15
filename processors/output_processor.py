"""
Process and write output data to JSON files.
"""
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from models.attraction import AttractionData, BaseAttraction, create_attraction
from utils.logger import log
from config.settings import OUTPUT_DIR, CHECKPOINT_ENABLED


class OutputProcessor:
    """Handles output file writing with checkpoints."""

    def __init__(self, output_filename: str = None):
        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Generate output filename if not provided
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"attractions_{timestamp}.json"

        self.output_filepath = OUTPUT_DIR / output_filename
        self.checkpoint_filepath = OUTPUT_DIR / f"{output_filename}.checkpoint"

        # Create subdirectory for individual attraction files
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.individual_dir = OUTPUT_DIR / f"attractions_{self.timestamp}"
        self.individual_dir.mkdir(parents=True, exist_ok=True)

        # Initialize data container
        self.data = AttractionData()

        # Track individual file paths
        self.individual_files = []

        # Load checkpoint if exists
        if CHECKPOINT_ENABLED:
            self._load_checkpoint()

    def _load_checkpoint(self):
        """Load data from checkpoint file if it exists."""
        if self.checkpoint_filepath.exists():
            try:
                with open(self.checkpoint_filepath, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)

                log.info(f"Loaded checkpoint from: {self.checkpoint_filepath}")

                # Reconstruct AttractionData from checkpoint
                # (simplified - in production you'd fully deserialize)
                self.data = AttractionData(**checkpoint_data)

            except Exception as e:
                log.error(f"Failed to load checkpoint: {e}")

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize attraction name for use as filename."""
        # Remove or replace invalid filename characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        # Replace spaces and special chars with underscores
        sanitized = re.sub(r'[\s\-\/]+', '_', sanitized)
        # Remove non-ASCII characters or keep only safe ones
        sanitized = re.sub(r'[^\w\-_]', '', sanitized)
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        # Ensure it's not empty
        if not sanitized:
            sanitized = f"attraction_{len(self.individual_files)}"
        return sanitized

    def add_attraction(self, attraction_data: Dict, attraction_type: str = None):
        """
        Add an attraction to the output data.

        Args:
            attraction_data: Dictionary with attraction data
            attraction_type: Optional type override
        """
        try:
            # Set type if provided
            if attraction_type and 'type' not in attraction_data:
                attraction_data['type'] = attraction_type

            # Create and validate attraction using Pydantic
            attraction = create_attraction(attraction_data)

            # Add to container
            self.data.add_attraction(attraction)

            # Write individual JSON file
            self._write_individual_file(attraction)

            log.info(f"Added attraction: {attraction.name}")

            # Save checkpoint after each addition
            if CHECKPOINT_ENABLED:
                self._save_checkpoint()

        except Exception as e:
            log.error(f"Failed to add attraction: {e}")
            # Add to failed list
            self.data.add_failed(
                str(attraction_data.get('google_maps_url', attraction_data.get('name', 'Unknown'))),
                str(e)
            )

    def _write_individual_file(self, attraction: BaseAttraction):
        """Write individual JSON file for an attraction."""
        try:
            # Generate filename from attraction name
            filename = self._sanitize_filename(attraction.name)
            filepath = self.individual_dir / f"{filename}.json"

            # Handle duplicate filenames
            counter = 1
            while filepath.exists():
                filepath = self.individual_dir / f"{filename}_{counter}.json"
                counter += 1

            # Write attraction data to individual file (exclude null values)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(
                    json.loads(attraction.model_dump_json(exclude_none=True)),
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            # Track the file
            self.individual_files.append({
                "name": attraction.name,
                "type": attraction.type,
                "file": filepath.name,
                "filepath": str(filepath.relative_to(OUTPUT_DIR))
            })

            log.debug(f"Wrote individual file: {filepath}")

        except Exception as e:
            log.error(f"Failed to write individual file for {attraction.name}: {e}")

    def add_failed_attraction(self, input_data: str, error: str):
        """Add a failed attraction attempt."""
        self.data.add_failed(input_data, error)
        log.warning(f"Added failed attraction: {input_data} - {error}")

    def _save_checkpoint(self):
        """Save current data to checkpoint file."""
        try:
            with open(self.checkpoint_filepath, 'w', encoding='utf-8') as f:
                json.dump(
                    json.loads(self.data.model_dump_json(exclude_none=True)),
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            log.debug(f"Checkpoint saved to: {self.checkpoint_filepath}")

        except Exception as e:
            log.error(f"Failed to save checkpoint: {e}")

    def finalize(self):
        """Finalize and write the index file."""
        # Update metadata
        stats = self.data.get_stats()

        # Create index file with metadata and references
        index_data = {
            "metadata": {
                "scraped_at": datetime.now().isoformat(),
                "version": "1.0.0",
                **stats
            },
            "output_directory": str(self.individual_dir.relative_to(OUTPUT_DIR)),
            "attractions": self.individual_files,
            "failed_attractions": self.data.failed_attractions
        }

        # Write index file
        index_filepath = OUTPUT_DIR / f"index_{self.timestamp}.json"
        try:
            with open(index_filepath, 'w', encoding='utf-8') as f:
                json.dump(
                    index_data,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            log.info(f"Index file saved to: {index_filepath}")
            log.info(f"Individual attraction files saved to: {self.individual_dir}")

            # Print statistics
            log.info(f"Statistics: {stats}")

            # Remove checkpoint file
            if CHECKPOINT_ENABLED and self.checkpoint_filepath.exists():
                self.checkpoint_filepath.unlink()
                log.debug("Checkpoint file removed")

            return index_filepath

        except Exception as e:
            log.error(f"Failed to write index file: {e}")
            return None

    def get_stats(self) -> Dict:
        """Get current statistics."""
        return self.data.get_stats()

    def get_processed_urls(self) -> List[str]:
        """Get list of URLs that have been processed."""
        processed = []

        for attractions_list in self.data.attractions.values():
            for attraction in attractions_list:
                if hasattr(attraction, 'google_maps_url') and attraction.google_maps_url:
                    processed.append(attraction.google_maps_url)

        return processed

    def write_error_log(self):
        """Write a separate error log file."""
        if not self.data.failed_attractions:
            return

        error_filepath = OUTPUT_DIR / f"{self.output_filepath.stem}_errors.json"

        try:
            with open(error_filepath, 'w', encoding='utf-8') as f:
                json.dump(
                    {"failed": self.data.failed_attractions},
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            log.info(f"Error log saved to: {error_filepath}")

        except Exception as e:
            log.error(f"Failed to write error log: {e}")
