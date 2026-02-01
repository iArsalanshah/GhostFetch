from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from scraper import StealthScraper, logger
from job_manager import JobManager
from config import settings
import uvicorn

app = FastAPI(title="Stealth Fetcher API", description="API for fetching content from hard-to-scrape sites.")
scraper = StealthScraper() 
job_manager = JobManager(scraper)

class FetchRequest(BaseModel):
    url: str
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
    If callback_url is provided, result will be POSTed there upon completion.
    """
    try:
        job_id = await job_manager.submit_job(request.url, request.callback_url, request.github_issue)
        return {"job_id": job_id, "url": request.url, "status": "queued"}
    except Exception as e:
        logger.exception("Error submitting job")
        raise HTTPException(status_code=500, detail=str(e))

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

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
