"""
GhostFetch Client - SDK for interacting with GhostFetch API.

Usage:
    from ghostfetch import GhostFetchClient
    
    client = GhostFetchClient()
    result = client.fetch_sync("https://example.com")
    print(result["markdown"])
"""

import requests
import time
import json
from typing import Optional, Dict, Any, Generator


class GhostFetchClient:
    """
    A Python SDK for interacting with the GhostFetch API.
    
    Supports both synchronous (blocking) and asynchronous (polling) fetch modes.
    
    Example:
        from ghostfetch import GhostFetchClient
        
        client = GhostFetchClient("http://localhost:8000")
        
        # Easy mode - blocks until complete
        result = client.fetch_sync("https://x.com/user/status/123")
        print(result["markdown"])
        
        # Async mode - for background processing
        job_id = client.fetch("https://example.com")
        result = client.wait_for_job(job_id)
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the GhostFetch client.
        
        Args:
            base_url: The base URL of the GhostFetch API server
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
    
    def fetch_sync(
        self, 
        url: str, 
        timeout: float = 120.0,
        context_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch a URL synchronously - blocks until the content is ready.
        
        This is the simplest way to fetch content from the API.
        
        Args:
            url: The URL to fetch
            timeout: Maximum time to wait (default: 120s)
            context_id: Optional context ID for session persistence
        
        Returns:
            dict with keys:
                - metadata: dict with title, author, publish_date, images
                - markdown: string with the page content as markdown
        
        Raises:
            requests.exceptions.HTTPError: If the request fails
            TimeoutError: If the request times out
        """
        payload = {
            "url": url,
            "context_id": context_id
        }
        response = self.session.post(
            f"{self.base_url}/fetch/sync",
            json=payload,
            timeout=timeout + 5  # Add buffer for network overhead
        )
        response.raise_for_status()
        return response.json()

    def fetch(
        self, 
        url: str, 
        context_id: Optional[str] = None, 
        callback_url: Optional[str] = None, 
        github_issue: Optional[int] = None
    ) -> str:
        """
        Submit an async fetch job and return the job ID immediately.
        
        Use wait_for_job() to poll for completion, or provide a callback_url
        to receive a webhook when the job completes.
        
        Args:
            url: The URL to fetch
            context_id: Optional context ID for session persistence
            callback_url: Optional webhook URL to receive results
            github_issue: Optional GitHub issue number to post results to
        
        Returns:
            str: The job ID
        """
        payload = {
            "url": url,
            "context_id": context_id,
            "callback_url": callback_url,
            "github_issue": github_issue
        }
        response = self.session.post(f"{self.base_url}/fetch", json=payload)
        response.raise_for_status()
        return response.json()["job_id"]

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get the current status and result of a job.
        
        Args:
            job_id: The job ID to check
        
        Returns:
            dict with job status and result (if completed)
        """
        response = self.session.get(f"{self.base_url}/job/{job_id}")
        response.raise_for_status()
        return response.json()

    def wait_for_job(
        self, 
        job_id: str, 
        poll_interval: float = 1.0, 
        timeout: float = 120.0
    ) -> Dict[str, Any]:
        """
        Poll the API until the job is completed or failed.
        
        Args:
            job_id: The job ID to wait for
            poll_interval: How often to poll in seconds (default: 1.0)
            timeout: Maximum time to wait in seconds (default: 120.0)
        
        Returns:
            dict with job status and result
        
        Raises:
            TimeoutError: If the job doesn't complete within timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            job = self.get_job(job_id)
            if job["status"] in ["completed", "failed"]:
                return job
            time.sleep(poll_interval)
        raise TimeoutError(f"Job {job_id} timed out after {timeout}s")

    def stream_events(self) -> Generator[Dict[str, Any], None, None]:
        """
        Subscribe to the SSE stream for real-time updates on all jobs.
        
        Yields:
            dict: Job update events
        """
        response = self.session.get(f"{self.base_url}/events", stream=True)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    yield json.loads(line[6:])

    def health(self) -> Dict[str, Any]:
        """
        Check the health of the GhostFetch API.
        
        Returns:
            dict with health status
        """
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def get_metrics(self) -> str:
        """
        Get Prometheus metrics from the API.
        
        Returns:
            str: Prometheus metrics in text format
        """
        response = self.session.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.text


# Convenience function for quick fetches via API
def fetch_via_api(
    url: str, 
    base_url: str = "http://localhost:8000",
    timeout: float = 120.0
) -> Dict[str, Any]:
    """
    Quick fetch via the GhostFetch API (synchronous).
    
    Example:
        from ghostfetch.client import fetch_via_api
        result = fetch_via_api("https://example.com")
    """
    client = GhostFetchClient(base_url)
    return client.fetch_sync(url, timeout=timeout)
