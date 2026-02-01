import asyncio
import uuid
import time
import requests
import sqlite3
import json
import os
import logging
from typing import Dict, Optional, List
from pydantic import BaseModel
from config import settings

logger = logging.getLogger("GhostFetch.JobManager")

class Job(BaseModel):
    id: str
    url: str
    callback_url: Optional[str] = None
    github_issue: Optional[int] = None
    status: str = "queued"
    result: Optional[dict] = None
    error: Optional[str] = None
    error_details: Optional[dict] = None
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

class JobManager:
    def __init__(self, scraper):
        self.scraper = scraper
        self.queue = asyncio.Queue()
        self.workers = []
        self._init_db()

    def _init_db(self):
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        self.db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    url TEXT,
                    callback_url TEXT,
                    github_issue INTEGER,
                    status TEXT,
                    result TEXT,
                    error TEXT,
                    error_details TEXT,
                    created_at REAL,
                    started_at REAL,
                    completed_at REAL
                )
            """)

    def _save_job(self, job: Job):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO jobs 
                (id, url, callback_url, github_issue, status, result, error, error_details, created_at, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id, job.url, job.callback_url, job.github_issue, job.status,
                json.dumps(job.result) if job.result else None,
                job.error,
                json.dumps(job.error_details) if job.error_details else None,
                job.created_at, job.started_at, job.completed_at
            ))

    def _get_job_from_db(self, job_id: str) -> Optional[Job]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row:
                data = dict(row)
                data["result"] = json.loads(data["result"]) if data["result"] else None
                data["error_details"] = json.loads(data["error_details"]) if data["error_details"] else None
                return Job(**data)
        return None

    async def start(self):
        for _ in range(settings.MAX_CONCURRENT_BROWSERS):
            worker = asyncio.create_task(self._worker())
            self.workers.append(worker)
        asyncio.create_task(self._cleanup_task())
        logger.info(f"Started {settings.MAX_CONCURRENT_BROWSERS} workers and cleanup task.")

    async def stop(self):
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        logger.info("Stopped workers.")

    async def submit_job(self, url: str, callback_url: Optional[str] = None, github_issue: Optional[int] = None) -> str:
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, url=url, callback_url=callback_url, github_issue=github_issue, created_at=time.time())
        self._save_job(job)
        await self.queue.put(job_id)
        logger.info(f"Job {job_id} submitted for {url}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._get_job_from_db(job_id)

    async def _worker(self):
        while True:
            job_id = await self.queue.get()
            job = self.get_job(job_id)
            if not job:
                self.queue.task_done()
                continue

            job.status = "processing"
            job.started_at = time.time()
            self._save_job(job)
            
            attempt = 0
            while attempt <= settings.MAX_REQUESTS_PER_BROWSER: # Note: This was max_retries in previous version, using settings.MAX_REQUESTS_PER_BROWSER as a stand-in or we can add MAX_RETRIES to config
                # Actually let's add MAX_RETRIES to config in a moment. For now hardcode 3.
                max_retries = 3
                try:
                    from scraper import ScraperError
                    logger.info(f"Worker processing job {job_id} for {job.url} (Attempt {attempt+1})")
                    result = await self.scraper.fetch(job.url)
                    job.result = result
                    job.status = "completed"
                    job.error = None
                    job.error_details = None
                    break
                except ScraperError as e:
                    logger.error(f"Scraper error for job {job_id}: {e.message}")
                    job.error = e.message
                    job.error_details = {"code": e.error_code, "retryable": e.retryable}
                    
                    if e.retryable and attempt < max_retries:
                        attempt += 1
                        import random
                        delay = (2 ** attempt) + random.uniform(0, 1)
                        logger.info(f"Retrying job {job_id} in {delay:.2f}s...")
                        await asyncio.sleep(delay)
                    else:
                        job.status = "failed"
                        break
                except Exception as e:
                    logger.exception(f"Fatal error for job {job_id}")
                    job.error = str(e)
                    job.error_details = {"code": "internal_error", "retryable": False}
                    job.status = "failed"
                    break
            
            job.completed_at = time.time()
            self._save_job(job)
            self.queue.task_done()
            
            if job.callback_url:
                asyncio.create_task(self._send_callback_async(job))
            
            if job.github_issue:
                asyncio.create_task(self._send_github_comment_async(job))

    async def _send_callback_async(self, job: Job):
        await asyncio.to_thread(self._send_callback, job)

    def _send_callback(self, job: Job):
        try:
            payload = {
                "job_id": job.id,
                "url": job.url,
                "status": job.status,
                "data": job.result,
                "error": job.error,
                "error_details": job.error_details
            }
            requests.post(job.callback_url, json=payload, timeout=10)
            logger.info(f"Callback sent for job {job.id} to {job.callback_url}")
        except Exception as e:
            logger.error(f"Failed to send callback for job {job.id}: {e}")

    async def _send_github_comment_async(self, job: Job):
        await asyncio.to_thread(self._send_github_comment, job)

    def _send_github_comment(self, job: Job):
        import subprocess
        try:
            repo = settings.GITHUB_REPO
            if job.status == "completed":
                size_kb = len(job.result.get("markdown", "")) / 1024
                body = f"✅ **Done**: Extracted {size_kb:.1f}KB markdown for {job.url}"
            else:
                retry_text = "(retryable)" if job.error_details and job.error_details.get("retryable") else "(fatal)"
                body = f"❌ **Failed**: {job.error} {retry_text}"
            
            subprocess.run(["gh", "issue", "comment", str(job.github_issue), "--body", body, "--repo", repo], check=True)
            logger.info(f"GitHub comment sent for job {job.id} to issue #{job.github_issue}")
        except Exception as e:
            logger.error(f"Failed to send GitHub comment for job {job.id}: {e}")

    async def _cleanup_task(self):
        while True:
            try:
                cutoff = time.time() - settings.JOB_TTL_SECONDS
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM jobs WHERE completed_at IS NOT NULL AND completed_at < ?", (cutoff,))
                logger.debug("Cleaned up old jobs from database.")
            except Exception as e:
                logger.error(f"Error in job cleanup task: {e}")
            await asyncio.sleep(3600) # Run every hour
