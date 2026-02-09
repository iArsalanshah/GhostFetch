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
from src.utils.config import settings
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger("GhostFetch.JobManager")

# Prometheus Metrics
JOBS_TOTAL = Counter("ghostfetch_jobs_total", "Total number of jobs processed", ["status"])
JOB_DURATION = Histogram("ghostfetch_job_duration_seconds", "Job processing duration in seconds")
ACTIVE_WORKERS = Gauge("ghostfetch_active_workers", "Number of currently active worker tasks")
QUEUE_SIZE = Gauge("ghostfetch_queue_size", "Current number of jobs in queue")

class Job(BaseModel):
    id: str
    url: str
    context_id: Optional[str] = None
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
        self.subscribers: List[asyncio.Queue] = []
        self._init_db()

    def _init_db(self):
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        self.db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    url TEXT,
                    context_id TEXT,
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
                (id, url, context_id, callback_url, github_issue, status, result, error, error_details, created_at, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id, job.url, job.context_id, job.callback_url, job.github_issue, job.status,
                json.dumps(job.result) if job.result else None,
                job.error,
                json.dumps(job.error_details) if job.error_details else None,
                job.created_at, job.started_at, job.completed_at
            ))
        self._broadcast({"type": "job_update", "job_id": job.id, "status": job.status})

    def _broadcast(self, data: dict):
        for q in self.subscribers:
            q.put_nowait(data)

    async def subscribe(self):
        q = asyncio.Queue()
        self.subscribers.append(q)
        try:
            while True:
                yield await q.get()
        finally:
            self.subscribers.remove(q)

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

    async def submit_job(self, url: str, context_id: Optional[str] = None, callback_url: Optional[str] = None, github_issue: Optional[int] = None) -> str:
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, url=url, context_id=context_id, callback_url=callback_url, github_issue=github_issue, created_at=time.time())
        self._save_job(job)
        await self.queue.put(job_id)
        logger.info(f"Job {job_id} submitted for {url}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._get_job_from_db(job_id)

    async def _worker(self):
        ACTIVE_WORKERS.inc()
        try:
            while True:
                QUEUE_SIZE.set(self.queue.qsize())
                job_id = await self.queue.get()
                job = self.get_job(job_id)
                if not job:
                    self.queue.task_done()
                    continue

                job.status = "processing"
                job.started_at = time.time()
                self._save_job(job)
                
                attempt = 0
                while attempt <= settings.MAX_RETRIES:
                    try:
                        from src.core.scraper import ScraperError
                        logger.info(f"Worker processing job {job_id} for {job.url} (Attempt {attempt+1})")
                        
                        with JOB_DURATION.time():
                            result = await self.scraper.fetch(job.url, context_id=job.context_id)

                        if not result or not isinstance(result, dict):
                            raise ScraperError(
                                "No content could be fetched from the URL",
                                "no_content",
                                retryable=True,
                            )
                        
                        job.result = result
                        job.status = "completed"
                        job.error = None
                        job.error_details = None
                        JOBS_TOTAL.labels(status="completed").inc()
                        break
                    except ScraperError as e:
                        logger.error(f"Scraper error for job {job_id}: {e.message}")
                        job.error = e.message
                        job.error_details = {"code": e.error_code, "retryable": e.retryable}
                        
                        if e.retryable and attempt < settings.MAX_RETRIES:
                            attempt += 1
                            import random
                            delay = (2 ** attempt) + random.uniform(0, 1)
                            logger.info(f"Retrying job {job_id} in {delay:.2f}s...")
                            await asyncio.sleep(delay)
                        else:
                            job.status = "failed"
                            JOBS_TOTAL.labels(status="failed").inc()
                            break
                    except Exception as e:
                        logger.exception(f"Fatal error for job {job_id}")
                        job.error = str(e)
                        job.error_details = {"code": "internal_error", "retryable": False}
                        job.status = "failed"
                        JOBS_TOTAL.labels(status="failed").inc()
                        break
                
                job.completed_at = time.time()
                self._save_job(job)
                self.queue.task_done()
                QUEUE_SIZE.set(self.queue.qsize())
                
                if job.callback_url:
                    asyncio.create_task(self._send_callback_async(job))
                
                if job.github_issue:
                    asyncio.create_task(self._send_github_comment_async(job))
        finally:
            ACTIVE_WORKERS.dec()

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
                markdown = job.result.get("markdown", "") if isinstance(job.result, dict) else ""
                size_kb = len(markdown) / 1024
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
