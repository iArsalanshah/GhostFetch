import requests
import time
import json
from typing import Optional, Dict, Any, Generator

class GhostFetchClient:
    """
    A simple Python SDK for interacting with the GhostFetch API.
    """
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def fetch(self, url: str, context_id: Optional[str] = None, callback_url: Optional[str] = None, github_issue: Optional[int] = None) -> str:
        """
        Submit a fetch job and return the job_id.
        """
        payload = {
            "url": url,
            "context_id": context_id,
            "callback_url": callback_url,
            "github_issue": github_issue
        }
        response = requests.post(f"{self.base_url}/fetch", json=payload)
        response.raise_for_status()
        return response.json()["job_id"]

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get the current status and result of a job.
        """
        response = requests.get(f"{self.base_url}/job/{job_id}")
        response.raise_for_status()
        return response.json()

    def wait_for_job(self, job_id: str, poll_interval: float = 1.0, timeout: float = 120.0) -> Dict[str, Any]:
        """
        Poll the API until the job is completed or failed.
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
        """
        response = requests.get(f"{self.base_url}/events", stream=True)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    yield json.loads(line[6:])

    def get_metrics(self) -> str:
        """
        Get Prometheus metrics.
        """
        response = requests.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.text

# Example usage:
if __name__ == "__main__":
    client = GhostFetchClient()
    url = "https://x.com/mrnacknack/status/2016134416897360212"
    
    print(f"Submitting job for {url}...")
    jid = client.fetch(url, context_id="research-session-1")
    
    print(f"Waiting for job {jid}...")
    result = client.wait_for_job(jid)
    
    if result["status"] == "completed":
        print("\n--- Metadata ---\n")
        print(json.dumps(result["result"]["metadata"], indent=2))
        print("\n--- Markdown ---\n")
        print(result["result"]["markdown"][:500] + "...")
    else:
        print(f"Job failed: {result['error']}")
