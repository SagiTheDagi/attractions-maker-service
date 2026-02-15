"""
Request and response schemas for the FastAPI endpoints.

Routes:
  POST /api/scrape/url         - Scrape a single Google Maps URL (synchronous)
  POST /api/scrape/batch       - Scrape multiple URLs (async job)
  POST /api/scrape/search      - Search and scrape attractions (async job)
  GET  /api/jobs/{job_id}      - Get job status and progress
  GET  /api/jobs/{job_id}/results - Get completed job results
  GET  /api/jobs               - List all jobs
  DELETE /api/jobs/{job_id}    - Cancel a running job
  GET  /api/health             - Health check
"""
from typing import Optional, List, Dict
from enum import Enum
from pydantic import BaseModel, Field


class ScrapeMode(str, Enum):
    MANUAL = "manual"
    AUTO = "auto"
    BOTH = "both"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Requests ──


class ScrapeUrlRequest(BaseModel):
    """POST /api/scrape/url - Scrape a single Google Maps URL."""
    url: str = Field(..., description="Google Maps URL to scrape")


class ScrapeBatchRequest(BaseModel):
    """POST /api/scrape/batch - Scrape multiple URLs as a background job."""
    urls: List[str] = Field(..., min_length=1, description="List of Google Maps URLs")
    output_filename: Optional[str] = None


class SearchItem(BaseModel):
    name: str
    city: Optional[str] = None
    type: Optional[str] = None


class ScrapeSearchRequest(BaseModel):
    """POST /api/scrape/search - Search Google Maps and scrape results."""
    search_items: List[SearchItem] = Field(..., min_length=1)
    mode: ScrapeMode = ScrapeMode.AUTO
    output_filename: Optional[str] = None


# ── Responses ──


class ScrapeUrlResponse(BaseModel):
    """Response for POST /api/scrape/url - returns scraped data directly."""
    data: Dict = Field(..., description="Scraped attraction data")


class JobCreatedResponse(BaseModel):
    """Returned when a batch/search job is created."""
    job_id: str
    status: JobStatus
    message: str


class JobProgressResponse(BaseModel):
    """GET /api/jobs/{job_id} - current progress of a scrape job."""
    job_id: str
    status: JobStatus
    total_urls: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    by_type: Dict[str, int] = Field(default_factory=dict)
    error: Optional[str] = None


class JobResultsResponse(BaseModel):
    """GET /api/jobs/{job_id}/results - full results of a completed job."""
    data: Dict = Field(
        default_factory=dict,
        description="Contains metadata, attractions (grouped by type), and failed_attractions"
    )


class HealthResponse(BaseModel):
    status: str = "ok"
    active_jobs: int = 0
