"""
Manages background scraping jobs with progress tracking.
"""
import asyncio
import uuid
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from api.schemas import JobStatus
from main import AttractionsScraper
from processors.data_processor import DataProcessor
from models.enums import AttractionType
from utils.logger import log
from config.settings import INPUT_DIR


class ScrapeJob:
    """Tracks the state of a single scrape job."""

    def __init__(self, job_id: str, input_file: str, mode: str = "manual",
                 output_filename: str = None):
        self.job_id = job_id
        self.input_file = input_file
        self.mode = mode
        self.output_filename = output_filename
        self.status = JobStatus.PENDING
        self.error: Optional[str] = None
        self.created_at = datetime.now().isoformat()
        self.task: Optional[asyncio.Task] = None
        self.scraper: Optional[AttractionsScraper] = None

    def get_progress(self) -> Dict:
        """Get current job progress from the scraper's output processor."""
        progress = {
            "job_id": self.job_id,
            "status": self.status,
            "total_urls": 0,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "by_type": {},
            "error": self.error,
        }

        if self.scraper:
            progress["total_urls"] = len(self.scraper.urls_queue)
            stats = self.scraper.output_processor.get_stats()
            progress["processed"] = stats["successful"] + stats["failed"]
            progress["successful"] = stats["successful"]
            progress["failed"] = stats["failed"]
            progress["by_type"] = stats["by_type"]

        return progress

    def get_results(self) -> Optional[Dict]:
        """Get final results if the job is completed."""
        if self.status != JobStatus.COMPLETED or not self.scraper:
            return None

        stats = self.scraper.output_processor.get_stats()
        data = self.scraper.output_processor.data

        # Serialize attractions grouped by type, with data quality info
        processor = DataProcessor()
        attractions = {}
        for type_key, type_attractions in data.attractions.items():
            serialized = []
            for a in type_attractions:
                entry = json.loads(a.model_dump_json(exclude_none=True))
                attraction_type = AttractionType(a.type)
                entry["data_quality"] = processor.get_data_quality_info(entry, attraction_type)
                serialized.append(entry)
            attractions[type_key] = serialized

        return {
            "metadata": {
                "scraped_at": datetime.now().isoformat(),
                **stats,
            },
            "attractions": attractions,
            "failed_attractions": data.failed_attractions,
        }


class JobManager:
    """Manages all scrape jobs."""

    def __init__(self):
        self.jobs: Dict[str, ScrapeJob] = {}

    def _write_temp_input(self, content: str, suffix: str = ".txt") -> str:
        """Write input data to a temp file and return its path."""
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
        tmp = INPUT_DIR / f"api_input_{uuid.uuid4().hex[:8]}{suffix}"
        tmp.write_text(content, encoding="utf-8")
        return str(tmp)

    async def create_url_batch_job(self, urls: list[str],
                                   output_filename: str = None) -> str:
        """Create a job that scrapes a list of URLs."""
        job_id = uuid.uuid4().hex[:12]
        input_file = self._write_temp_input("\n".join(urls), suffix=".txt")

        job = ScrapeJob(job_id, input_file, mode="manual",
                        output_filename=output_filename)
        self.jobs[job_id] = job

        job.task = asyncio.create_task(self._run_job(job))
        return job_id

    async def create_search_job(self, search_items: list[dict],
                                mode: str = "auto",
                                output_filename: str = None) -> str:
        """Create a job that searches and scrapes attractions."""
        job_id = uuid.uuid4().hex[:12]

        # Write search items as CSV
        lines = ["name,city,type"]
        for item in search_items:
            name = item.get("name", "")
            city = item.get("city", "")
            atype = item.get("type", "")
            lines.append(f"{name},{city},{atype}")

        input_file = self._write_temp_input("\n".join(lines), suffix=".csv")

        job = ScrapeJob(job_id, input_file, mode=mode,
                        output_filename=output_filename)
        self.jobs[job_id] = job

        job.task = asyncio.create_task(self._run_job(job))
        return job_id

    async def _run_job(self, job: ScrapeJob):
        """Execute a scrape job in the background."""
        try:
            job.status = JobStatus.RUNNING
            log.info(f"Job {job.job_id}: starting scrape")

            job.scraper = AttractionsScraper(
                input_file=job.input_file,
                output_file=job.output_filename,
                mode=job.mode,
            )
            await job.scraper.run()

            job.status = JobStatus.COMPLETED
            log.info(f"Job {job.job_id}: completed")

        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLED
            log.warning(f"Job {job.job_id}: cancelled")
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            log.error(f"Job {job.job_id}: failed - {e}")
        finally:
            # Clean up temp input file
            try:
                Path(job.input_file).unlink(missing_ok=True)
            except Exception:
                pass

    def get_job(self, job_id: str) -> Optional[ScrapeJob]:
        return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job or not job.task:
            return False
        if job.status == JobStatus.RUNNING:
            job.task.cancel()
            return True
        return False

    def list_jobs(self) -> list[Dict]:
        return [job.get_progress() for job in self.jobs.values()]

    @property
    def active_job_count(self) -> int:
        return sum(1 for j in self.jobs.values()
                   if j.status in (JobStatus.PENDING, JobStatus.RUNNING))
