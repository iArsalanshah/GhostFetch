import asyncio
import uuid
import time
import requests
from typing import Dict, Optional
from pydantic import BaseModel

class Job(BaseModel):
    id: str
    url: str
    callback_url: Optional[str] = None
    github_issue: Optional[int] = None
    status: str = "queued"
    result: Optional[Dict] = None
    error: Optional[str] = None
    error_details: Optional[Dict] = None
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

class JobManager:
    def __init__(self, scraper, max_concurrent=2, max_retries=3):
        self.scraper = scraper
        self.jobs: Dict[str, Job] = {}
        self.queue = asyncio.Queue()
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.workers = []

    async def start(self):
        for _ in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker())
            self.workers.append(worker)

    async def stop(self):
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)

    async def submit_job(self, url: str, callback_url: Optional[str] = None, github_issue: Optional[int] = None) -> str:
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, url=url, callback_url=callback_url, github_issue=github_issue, created_at=time.time())
        self.jobs[job_id] = job
        await self.queue.put(job_id)
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    async def _worker(self):
        import random
        while True:
            job_id = await self.queue.get()
            job = self.jobs[job_id]
            job.status = "processing"
            job.started_at = time.time()
            
            attempt = 0
            while attempt <= self.max_retries:
                try:
                    from scraper import ScraperError
                    print(f"Worker processing job {job_id} for {job.url} (Attempt {attempt+1})")
                    result = await self.scraper.fetch(job.url)
                    job.result = result
                    job.status = "completed"
                    job.error = None
                    job.error_details = None
                    break
                except ScraperError as e:
                    print(f"Scraper error for job {job_id}: {e.message}")
                    job.error = e.message
                    job.error_details = {"code": e.error_code, "retryable": e.retryable}
                    
                    if e.retryable and attempt < self.max_retries:
                        attempt += 1
                        delay = (2 ** attempt) + random.uniform(0, 1)
                        print(f"Retrying job {job_id} in {delay:.2f}s...")
                        await asyncio.sleep(delay)
                    else:
                        job.status = "failed"
                        break
                except Exception as e:
                    print(f"Fatal error for job {job_id}: {e}")
                    job.error = str(e)
                    job.error_details = {"code": "internal_error", "retryable": False}
                    job.status = "failed"
                    break
            
            job.completed_at = time.time()
            self.queue.task_done()
            
            if job.callback_url:
                self._send_callback(job)
            
            if job.github_issue:
                self._send_github_comment(job)

    def _send_github_comment(self, job: Job):
        import subprocess
        try:
            repo = "iArsalanshah/GhostFetch"
            if job.status == "completed":
                size_kb = len(job.result.get("markdown", "")) / 1024
                body = f"✅ **Done**: Extracted {size_kb:.1f}KB markdown for {job.url}"
            else:
                retry_text = "(retryable)" if job.error_details and job.error_details.get("retryable") else "(fatal)"
                body = f"❌ **Failed**: {job.error} {retry_text}"
            
            subprocess.run(["gh", "issue", "comment", str(job.github_issue), "--body", body, "--repo", repo], check=True)
            print(f"GitHub comment sent for job {job.id} to issue #{job.github_issue}")
        except Exception as e:
            print(f"Failed to send GitHub comment for job {job.id}: {e}")

    def _send_callback(self, job: Job):
        try:
            payload = {
                "job_id": job.id,
                "url": job.url,
                "status": job.status,
                "data": job.result, # Contains metadata and markdown
                "error": job.error,
                "error_details": job.error_details
            }
            requests.post(job.callback_url, json=payload, timeout=10)
            print(f"Callback sent for job {job.id} to {job.callback_url}")
        except Exception as e:
            print(f"Failed to send callback for job {job.id}: {e}")
