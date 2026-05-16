from fastapi import FastAPI, HTTPException, Request, Query, Header, Depends
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import json
import asyncio
from contextlib import asynccontextmanager
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.core.scraper import StealthScraper, ScraperError, logger
from src.core.job_manager import JobManager
from src.utils.config import settings
from src.utils.security import (
    validate_target_url,
    validate_callback_url,
    validate_context_id,
    URLValidationError,
)
from ghostfetch.version import __version__


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.REQUIRE_API_KEY and not settings.API_KEY:
        logger.warning(
            "SECURITY: REQUIRE_API_KEY is enabled but GHOSTFETCH_API_KEY is not set. "
            "All authenticated fetch endpoints will reject requests."
        )
    logger.info("Starting Playwright browser and job manager...")
    await scraper.start()
    await job_manager.start()
    logger.info("Browser and Job Manager started.")
    try:
        yield
    finally:
        logger.info("Stopping Playwright browser and job manager...")
        await job_manager.stop()
        await scraper.stop()
        logger.info("Stopped.")

app = FastAPI(
    title="GhostFetch API", 
    description="Stealthy headless browser API for AI agents. Fetches content from hard-to-scrape sites and converts to Markdown.",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)
scraper = StealthScraper() 
job_manager = JobManager(scraper)


class FetchRequest(BaseModel):
    """Request body for fetch endpoints."""
    url: str = Field(..., description="The URL to fetch")
    context_id: Optional[str] = Field(None, description="Context ID for session persistence (cookies/localStorage)")
    callback_url: Optional[str] = Field(None, description="Webhook URL to receive results when job completes")
    github_issue: Optional[int] = Field(None, ge=1, description="GitHub issue number to post results as a comment")


class SyncFetchRequest(BaseModel):
    """Request body for synchronous fetch endpoint."""
    url: str = Field(..., description="The URL to fetch")
    context_id: Optional[str] = Field(None, description="Context ID for session persistence")
    timeout: Optional[float] = Field(
        None,
        ge=0.0,
        description=f"Maximum time to wait in seconds (default: {settings.SYNC_TIMEOUT_DEFAULT}, max: {settings.MAX_SYNC_TIMEOUT})"
    )


def _enforce_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    if not settings.REQUIRE_API_KEY:
        return
    if not settings.API_KEY:
        raise HTTPException(status_code=503, detail="API key auth is enabled but GHOSTFETCH_API_KEY is not configured")
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _normalize_success_response(url: str, result: dict) -> dict:
    return {
        "metadata": result.get("metadata", {}),
        "markdown": result.get("markdown", ""),
        "url": url,
        "status": "success",
    }


@app.post("/fetch", status_code=202)
async def fetch_endpoint(request: FetchRequest, _: None = Depends(_enforce_api_key)):
    """
    Submit a fetch job (async). Returns a job ID immediately.
    
    Use GET /job/{job_id} to poll for results, or provide a callback_url
    to receive a webhook when the job completes.
    
    For synchronous fetching, use POST /fetch/sync instead.
    """
    try:
        url = validate_target_url(request.url)
        context_id = validate_context_id(request.context_id)
        callback_url = validate_callback_url(request.callback_url)
        job_id = await job_manager.submit_job(
            url,
            context_id=context_id,
            callback_url=callback_url,
            github_issue=request.github_issue
        )
        return {"job_id": job_id, "url": url, "status": "queued"}
    except URLValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error submitting job")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fetch/sync", status_code=200)
async def fetch_sync_endpoint(request: SyncFetchRequest, _: None = Depends(_enforce_api_key)):
    """
    Fetch a URL synchronously - blocks until content is ready.
    
    This is the easiest way for AI agents to fetch content:
    one request in, structured content out.
    
    Returns:
        - metadata: dict with title, author, publish_date, images
        - markdown: string with the page content as markdown
    
    Example:
        curl -X POST "http://localhost:8000/fetch/sync" \\
             -H "Content-Type: application/json" \\
             -d '{"url": "https://example.com"}'
    """
    # Use default timeout if not specified, cap at max allowed
    timeout = request.timeout if request.timeout is not None else settings.SYNC_TIMEOUT_DEFAULT
    timeout = min(max(timeout, 1), settings.MAX_SYNC_TIMEOUT)
    
    try:
        url = validate_target_url(request.url)
        context_id = validate_context_id(request.context_id)
        # Direct fetch with timeout
        result = await asyncio.wait_for(
            scraper.fetch(url, context_id=context_id),
            timeout=timeout
        )
        
        if not result:
            raise HTTPException(
                status_code=502, 
                detail="No content could be fetched from the URL"
            )
        
        return _normalize_success_response(url, result)
        
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, 
            detail=f"Request timed out after {timeout} seconds"
        )
    except ScraperError as e:
        status_code = 502 if e.retryable else 400
        raise HTTPException(status_code=status_code, detail=e.message)
    except URLValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error in sync fetch")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fetch/sync", status_code=200)
async def fetch_sync_get_endpoint(
    url: str = Query(..., description="The URL to fetch"),
    context_id: Optional[str] = Query(None, description="Context ID for session persistence"),
    timeout: Optional[float] = Query(
        None,
        ge=0.0,
        description=f"Maximum time to wait in seconds (default: {settings.SYNC_TIMEOUT_DEFAULT}, max: {settings.MAX_SYNC_TIMEOUT})"
    ),
    _: None = Depends(_enforce_api_key)
):
    """
    Fetch a URL synchronously via GET request.
    
    Convenience endpoint for simple requests:
        curl "http://localhost:8000/fetch/sync?url=https://example.com"
    """
    request = SyncFetchRequest(url=url, context_id=context_id, timeout=timeout)
    return await fetch_sync_endpoint(request)


@app.get("/events")
async def sse_endpoint(request: Request, _: None = Depends(_enforce_api_key)):
    """
    Server-Sent Events (SSE) endpoint for real-time job updates.
    """
    async def event_generator():
        async for event in job_manager.subscribe():
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/job/{job_id}")
async def get_job_status(job_id: str, _: None = Depends(_enforce_api_key)):
    """
    Get the status and result of a fetch job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/health")
async def health_check():
    browser_ok = scraper.browser and scraper.browser.is_connected()
    return {
        "status": "ok",
        "browser_connected": browser_ok,
        "active_jobs_queue": job_manager.queue.qsize(),
        "active_browser_contexts": scraper.get_active_contexts_count(),
        "concurrency_limit": settings.MAX_CONCURRENT_BROWSERS
    }

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
