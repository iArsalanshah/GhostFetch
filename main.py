from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logging
import json
import asyncio
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.core.scraper import StealthScraper, logger
from src.core.job_manager import JobManager
from src.utils.config import settings

app = FastAPI(title="Stealth Fetcher API", description="API for fetching content from hard-to-scrape sites.")
scraper = StealthScraper() 
job_manager = JobManager(scraper)

class FetchRequest(BaseModel):
    url: str
    context_id: Optional[str] = None
    callback_url: Optional[str] = None
    github_issue: Optional[int] = None

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Playwright browser and job manager...")
    await scraper.start()
    await job_manager.start()
    logger.info("Browser and Job Manager started.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Stopping Playwright browser and job manager...")
    await job_manager.stop()
    await scraper.stop()
    logger.info("Stopped.")

@app.post("/fetch", status_code=202)
async def fetch_endpoint(request: FetchRequest):
    """
    Submit a fetch job. Returns a job ID immediately.
    If context_id is provided, it will reuse/save cookies for that context.
    If callback_url is provided, result will be POSTed there upon completion.
    """
    try:
        job_id = await job_manager.submit_job(
            request.url, 
            context_id=request.context_id,
            callback_url=request.callback_url, 
            github_issue=request.github_issue
        )
        return {"job_id": job_id, "url": request.url, "status": "queued"}
    except Exception as e:
        logger.exception("Error submitting job")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events")
async def sse_endpoint(request: Request):
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
async def get_job_status(job_id: str):
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
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
