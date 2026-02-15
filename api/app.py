"""
FastAPI application for the Google Maps attractions scraper.

Routes:
  POST /api/scrape/url              - Scrape a single Google Maps URL (sync)
  POST /api/scrape/batch            - Scrape multiple URLs (async job)
  POST /api/scrape/search           - Search and scrape (async job)
  GET  /api/jobs                    - List all jobs
  GET  /api/jobs/{job_id}           - Job progress
  GET  /api/jobs/{job_id}/results   - Job results
  DELETE /api/jobs/{job_id}         - Cancel a job
  GET  /api/health                  - Health check
"""
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    ScrapeUrlRequest, ScrapeUrlResponse,
    ScrapeBatchRequest, ScrapeSearchRequest,
    JobCreatedResponse, JobProgressResponse, JobResultsResponse,
    JobStatus, HealthResponse,
)
from api.job_manager import JobManager
from utils.browser_manager import BrowserManager
from utils.rate_limiter import RateLimiter
from scrapers.detail_scraper import DetailScraper
from processors.data_processor import DataProcessor
from models.enums import AttractionType
from models.attraction import create_attraction
from utils.logger import log


# ── Shared state ──

job_manager = JobManager()
# Reusable browser for single-URL scrapes (avoids cold-start per request)
_browser: BrowserManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global _browser
    _browser = BrowserManager()
    await _browser.start()
    log.info("API browser manager started")
    yield
    if _browser:
        await _browser.close()
        log.info("API browser manager closed")


app = FastAPI(
    title="Attractions Scraper API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow your React frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",     # Vite dev
        "http://localhost:3000",
        "https://*.vercel.app",      # Vercel preview deploys
        # TODO: add your production domain here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  POST /api/scrape/url  — single URL, sync
# ─────────────────────────────────────────────

@app.post("/api/scrape/url", response_model=ScrapeUrlResponse)
async def scrape_single_url(body: ScrapeUrlRequest):
    """
    Scrape a single Google Maps URL and return the data directly.

    Request:  {"url": "https://www.google.com/maps/place/..."}
    Response: {"data": { ...attraction fields... }}
    """
    global _browser
    if not _browser or not _browser.page:
        raise HTTPException(status_code=503, detail="Browser not ready")

    url = body.url
    valid_hosts = ("google.com/maps", "maps.app.goo.gl", "goo.gl/maps")
    if not any(host in url for host in valid_hosts):
        raise HTTPException(status_code=400, detail="URL must be a Google Maps URL")

    try:
        # Navigate
        success = await _browser.navigate(url)
        if not success:
            raise HTTPException(status_code=502, detail="Failed to load the page")

        # Extract
        detail_scraper = DetailScraper(_browser.page)
        raw_data = await detail_scraper.extract_all(url)

        # Clean & enrich
        processor = DataProcessor()
        raw_data = processor.clean_data(raw_data)

        if "type" not in raw_data:
            inferred = processor.infer_attraction_type(
                raw_data.get("category"), url
            )
            raw_data["type"] = inferred.value if inferred else AttractionType.ACTIVITY.value

        attraction_type = AttractionType(raw_data["type"])
        quality_info = processor.get_data_quality_info(raw_data, attraction_type)

        # Validate through Pydantic model
        attraction = create_attraction(raw_data)
        data = json.loads(attraction.model_dump_json(exclude_none=True))
        data["data_quality"] = quality_info

        return ScrapeUrlResponse(data=data)

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Single URL scrape failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  POST /api/scrape/batch  — multiple URLs, async
# ─────────────────────────────────────────────

@app.post("/api/scrape/batch", response_model=JobCreatedResponse)
async def scrape_batch(body: ScrapeBatchRequest):
    """
    Start a background job to scrape multiple Google Maps URLs.

    Request:  {"urls": ["https://...", "https://..."]}
    Response: {"job_id": "abc123", "status": "pending", "message": "..."}
    """
    job_id = await job_manager.create_url_batch_job(
        urls=body.urls,
        output_filename=body.output_filename,
    )
    return JobCreatedResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message=f"Job created with {len(body.urls)} URLs",
    )


# ─────────────────────────────────────────────
#  POST /api/scrape/search  — search mode, async
# ─────────────────────────────────────────────

@app.post("/api/scrape/search", response_model=JobCreatedResponse)
async def scrape_search(body: ScrapeSearchRequest):
    """
    Start a background job to search Google Maps and scrape results.

    Request:  {"search_items": [{"name": "...", "city": "..."}], "mode": "auto"}
    Response: {"job_id": "abc123", "status": "pending", "message": "..."}
    """
    items = [item.model_dump() for item in body.search_items]
    job_id = await job_manager.create_search_job(
        search_items=items,
        mode=body.mode.value,
        output_filename=body.output_filename,
    )
    return JobCreatedResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message=f"Search job created with {len(items)} items",
    )


# ─────────────────────────────────────────────
#  GET /api/jobs  — list all jobs
# ─────────────────────────────────────────────

@app.get("/api/jobs")
async def list_jobs():
    """List all scrape jobs with their current progress."""
    return job_manager.list_jobs()


# ─────────────────────────────────────────────
#  GET /api/jobs/{job_id}  — job progress
# ─────────────────────────────────────────────

@app.get("/api/jobs/{job_id}", response_model=JobProgressResponse)
async def get_job_progress(job_id: str):
    """Get the current progress of a scrape job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.get_progress()


# ─────────────────────────────────────────────
#  GET /api/jobs/{job_id}/results  — completed results
# ─────────────────────────────────────────────

@app.get("/api/jobs/{job_id}/results", response_model=JobResultsResponse)
async def get_job_results(job_id: str):
    """
    Get the full results of a completed scrape job.

    Response: {"data": {"metadata": {...}, "attractions": {...}, "failed_attractions": [...]}}
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Job still running")

    if job.status == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail=f"Job failed: {job.error}")

    results = job.get_results()
    if not results:
        raise HTTPException(status_code=404, detail="No results available")

    return JobResultsResponse(data=results)


# ─────────────────────────────────────────────
#  DELETE /api/jobs/{job_id}  — cancel a job
# ─────────────────────────────────────────────

@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running scrape job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_manager.cancel_job(job_id):
        return {"message": f"Job {job_id} cancelled"}
    else:
        raise HTTPException(
            status_code=409,
            detail=f"Job cannot be cancelled (status: {job.status})",
        )


# ─────────────────────────────────────────────
#  GET /api/health
# ─────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(active_jobs=job_manager.active_job_count)
