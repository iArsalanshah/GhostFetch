from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from scraper import StealthScraper
from job_manager import JobManager
import uvicorn

app = FastAPI(title="Stealth Fetcher API", description="API for fetching content from hard-to-scrape sites.")
# On a MacBook Pro 2018 with 8GB RAM, we limit to 2 concurrent browser contexts
scraper = StealthScraper(max_concurrent=2) 
job_manager = JobManager(scraper, max_concurrent=2)

class FetchRequest(BaseModel):
    url: str
    callback_url: Optional[str] = None
    github_issue: Optional[int] = None

@app.on_event("startup")
async def startup_event():
    print("Starting Playwright browser and job manager...")
    await scraper.start()
    await job_manager.start()
    print("Browser and Job Manager started.")

@app.on_event("shutdown")
async def shutdown_event():
    print("Stopping Playwright browser and job manager...")
    await job_manager.stop()
    await scraper.stop()
    print("Stopped.")

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
        "active_jobs": job_manager.queue.qsize(),
        "concurrency_limit": scraper.semaphore._value
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
