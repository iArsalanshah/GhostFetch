# GhostFetch

[![PyPI version](https://img.shields.io/pypi/v/ghostfetch?color=blue)](https://pypi.org/project/ghostfetch/)
[![Docker Hub](https://img.shields.io/docker/pulls/iarsalanshah/ghostfetch)](https://hub.docker.com/r/iarsalanshah/ghostfetch)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A stealthy headless browser service for AI agents. Bypasses anti-bot protections to fetch content from sites like X.com and converts it to clean Markdown.

## Features
- **Zero Setup**: Install with pip, browsers auto-install on first run
- **Synchronous API**: Single request returns content directly (no polling needed)
- **Ghost Protocol**: Advanced proxy rotation and cohesive browser fingerprinting
- **Stealth Browsing**: Uses Playwright with custom flags and canvas noise injection
- **Markdown Output**: Automatically converts HTML to Markdown for easy LLM consumption
- **Metadata Extraction**: Automatically extracts title, author, publish date, and images
- **Dynamic Smart Scrolling**: Automatically detects and scrolls infinite-feed pages until full content is loaded
- **X.com Support**: Specific logic to wait for tweet content to render before scrolling
- **Async Job Queue**: Process multiple requests concurrently with intelligent retry
- **Persistent Sessions**: Cookie/localStorage persistence per domain
- **Webhook Callbacks**: Get notified via HTTP when jobs complete
- **GitHub Integration**: Post results directly to GitHub issues
- **Dual Mode**: CLI tool or REST API service
- **Docker Ready**: Pre-configured Docker setup with docker-compose

## How It Works

GhostFetch bridges the gap between AI agents and complex web content:

1.  **Request**: You send a URL to the API (Sync or Async).
2.  **Stealth Browser**: A headless Playwright instance initializes with "Ghost Protocol" (fingerprint masking, canvas noise, proxy rotation).
3.  **Smart Interaction**: The browser navigates, waits for hydration, and intelligently scrolls to trigger lazy-loading (e.g., full Twitter threads).
4.  **Extraction**: DOM is parsed and converted to clean, LLM-optimized Markdown.
5.  **Response**: JSON result is returned or posted to a webhook/GitHub issue.

## Quick Start

### For AI Agents (Simplest)

```bash
# Install from PyPI
pip install ghostfetch

# Fetch any URL (auto-installs browsers on first run)
ghostfetch "https://x.com/user/status/123"

# Or use the Python SDK
python -c "from ghostfetch import fetch; print(fetch('https://example.com')['markdown'])"
```

### For API Usage

```bash
# Start the server
ghostfetch serve

# Fetch synchronously (blocks until done)
curl "http://localhost:8000/fetch/sync?url=https://example.com"
```

## Installation

### Option 1: Docker Hub (Fastest)

```bash
# Pull and run
docker run -p 8000:8000 iarsalanshah/ghostfetch

# Or with docker-compose
docker-compose up
```

### Option 2: pip install

```bash
# From PyPI
pip install ghostfetch

# Or from source
git clone https://github.com/iArsalanshah/GhostFetch.git
cd GhostFetch
pip install -e .

# Browsers install automatically on first use, or run:
ghostfetch setup
```

### Option 3: Manual Setup

```bash
cd GhostFetch

# Create virtual environment (optional)
python3 -m venv venv
source venv/bin/activate

# Install packages & browser
pip install -r requirements.txt
playwright install chromium
```

## Usage

### 1. CLI Mode (Zero Setup)

Using the `ghostfetch` CLI (after pip install):

```bash
# Basic fetch
ghostfetch "https://x.com/user/status/123"

# JSON output (for parsing)
ghostfetch "https://example.com" --json

# Metadata only
ghostfetch "https://example.com" --metadata-only

# Quiet mode (no progress messages)
ghostfetch "https://example.com" --quiet
```

Using the legacy module directly:
```bash
python -m src.core.scraper "https://x.com/user/status/123"
```

Output:
```
--- Metadata ---
{
  "title": "...",
  "author": "...",
  "publish_date": "...",
  "images": [...]
}

--- Markdown ---
[converted markdown content]
```

### 2. API Mode (Service for Agents)

Start the server:
```bash
# Using CLI
ghostfetch serve

# Or directly
python main.py
```
The server will start at `http://localhost:8000`.

## API Endpoints

### Synchronous Fetch (Recommended for AI Agents)
- **POST** `/fetch/sync` — blocks until content is ready
- **GET** `/fetch/sync?url=...` — same, but via query parameter

**Example (POST):**
```bash
curl -X POST "http://localhost:8000/fetch/sync" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com", "timeout": 60}'
```

**Example (GET):**
```bash
curl "http://localhost:8000/fetch/sync?url=https://example.com"
```

**Response:**
```json
{
  "metadata": {
    "title": "Example Domain",
    "author": "",
    "publish_date": "",
    "images": []
  },
  "markdown": "# Example Domain\n\nThis domain is for use in illustrative examples..."
}
```

### Async Fetch (For Background Processing)
- **POST** `/fetch` (returns `202 Accepted`)
- **Body**: 
  ```json
  {
    "url": "https://example.com",
    "callback_url": "https://your-server.com/webhook",
    "github_issue": 123
  }
  ```

**Example:**
```bash
curl -X POST "http://localhost:8000/fetch" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://x.com/user/status/123"}'
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890",
  "url": "https://x.com/user/status/123",
  "status": "queued"
}
```

### Check Job Status
- **GET** `/job/{job_id}`

**Example:**
```bash
curl "http://localhost:8000/job/a1b2c3d4-e5f6-7890"
```

**Response (Completed):**
```json
{
  "id": "a1b2c3d4-e5f6-7890",
  "url": "https://x.com/mrnacknack/status/2016134416897360212",
  "status": "completed",
  "result": {
    "metadata": {
      "title": "...",
      "author": "...",
      "publish_date": "...",
      "images": [...]
    },
    "markdown": "..."
  },
  "created_at": 1706000000,
  "started_at": 1706000001,
  "completed_at": 1706000010
}
```

### Health Check
- **GET** `/health`

**Response:**
```json
{
  "status": "ok",
  "browser_connected": true,
  "active_jobs_queue": 2,
  "active_browser_contexts": 1,
  "concurrency_limit": 2
}
```

## Integration Examples

### Python Agent with Job Polling
```python
import requests
import time

def fetch_content_async(url):
    # Submit job
    response = requests.post(
        "http://localhost:8000/fetch",
        json={"url": url}
    )
    job_id = response.json()["job_id"]
    
    # Poll until completed
    while True:
        job_response = requests.get(f"http://localhost:8000/job/{job_id}")
        job = job_response.json()
        
        if job["status"] == "completed":
            return job["result"]["markdown"]
        elif job["status"] == "failed":
            raise Exception(f"Job failed: {job['error']}")
        
        time.sleep(1)  # Poll every second
```

### Using Webhook Callbacks
```python
import requests

# Your webhook endpoint receives:
# POST to callback_url with:
# {
#   "job_id": "...",
#   "url": "...",
#   "status": "completed",
#   "data": {"metadata": {...}, "markdown": "..."},
#   "error": null,
#   "error_details": null
# }

requests.post(
    "http://localhost:8000/fetch",
    json={
        "url": "https://example.com",
        "callback_url": "https://your-server.com/webhooks/ghostfetch"
    }
)
```

### GitHub Integration
When you include a `github_issue` parameter, GhostFetch will post results as comments:

```python
requests.post(
    "http://localhost:8000/fetch",
    json={
        "url": "https://example.com",
        "github_issue": 42  # Post result as comment on issue #42
    }
)
```

**Requires:**
- GitHub CLI (`gh` command) installed
- `GITHUB_TOKEN` environment variable set
- `GITHUB_REPO` configured

## Integration with AI Agents
Your agent can submit a fetch job and poll for results:

```python
import requests
import time

def fetch_blocked_content(url):
    response = requests.post(
        "http://localhost:8000/fetch",
        json={"url": url}
    )
    job_id = response.json()["job_id"]
    
    # Poll for completion
    max_retries = 60
    for _ in range(max_retries):
        result = requests.get(f"http://localhost:8000/job/{job_id}").json()
        if result["status"] == "completed":
            return result["result"]["markdown"]
        elif result["status"] == "failed":
            return f"Error: {result['error']}"
        time.sleep(1)
    
    return "Timeout waiting for result"
```

## Configuration
    
### Project Structure

```bash
ghostfetch/
├── ghostfetch/           # Core package
│   ├── cli.py            # CLI entry point
│   └── mcp_server.py     # MCP integration
├── src/
│   ├── core/
│   │   └── scraper.py    # Main scraping logic
│   └── utils/
├── storage/              # Runtime data
│   ├── jobs.db           # SQLite job history
│   └── scraper.log       # Application logs
├── docker-compose.yml
└── pyproject.toml
```

GhostFetch is configured via environment variables (see `src/utils/config.py`) or the `proxies.txt` file.

- **Proxies**: Add one proxy per line to `proxies.txt` in the format `http://user:pass@host:port`.
- **Strategy**: Set `PROXY_STRATEGY` to `round_robin` or `random`.

### Environment Variables

```bash
# API Server
GHOSTFETCH_HOST=0.0.0.0
GHOSTFETCH_PORT=8000

# Scraper Settings
MAX_CONCURRENT_BROWSERS=2          # Number of concurrent browser contexts
MIN_DOMAIN_DELAY=10                # Minimum seconds between requests to same domain
MAX_REQUESTS_PER_BROWSER=50        # Restart browser after N requests
MAX_RETRIES=3                      # Retry attempts for failed requests

# Sync Endpoint Settings
SYNC_TIMEOUT_DEFAULT=120           # Default timeout for /fetch/sync (seconds)
MAX_SYNC_TIMEOUT=300               # Maximum allowed timeout (5 minutes)

# GitHub Integration
GITHUB_REPO=iArsalanshah/GhostFetch  # Owner/repo for issue comments

# Persistence
DATABASE_URL=sqlite:///./storage/jobs.db
STORAGE_DIR=storage

# Job Lifecycle
JOB_TTL_SECONDS=86400              # Delete completed jobs after 24 hours
```

### Docker Environment
Create a `.env` file for docker-compose:

```bash
MAX_CONCURRENT_BROWSERS=2
MIN_DOMAIN_DELAY=10
GITHUB_REPO=your-org/your-repo
JOB_TTL_SECONDS=86400
```

Then run:
```bash
docker-compose --env-file .env up
```

## Specific Handling
- **Universal Smart Scrolling**: The scraper intelligently detects page height changes and scrolls until no new content is loaded. This allows it to capture:
    - Long X.com/Twitter threads
    - Infinite scroll blogs/feeds
    - Single Page Applications only rendering visible content
    - Safety limits (50 scrolls) prevent infinite loops
- **X/Twitter**: In addition to smart scrolling, the scraper specifically waits for `[data-testid="tweetText"]` to ensure the core tweet is present before starting the scroll.

## ⚠️ Important: Rate Limiting & Ethics

This tool bypasses anti-bot protections. **Use responsibly:**

- **Respect robots.txt** - Check site policies before scraping
- **Implement delays** - Use `MIN_DOMAIN_DELAY` (default: 10 seconds) to avoid overloading servers
- **Throttle requests** - Reduce `MAX_CONCURRENT_BROWSERS` for high-volume scraping
- **Terms of Service** - Ensure your use complies with target site's ToS
- **Authentication** - When possible, use authorized access instead of bypassing protections

### Recommended Settings for Production
```bash
# Conservative (respectful scraping)
MIN_DOMAIN_DELAY=30
MAX_CONCURRENT_BROWSERS=1

# Moderate
MIN_DOMAIN_DELAY=15
MAX_CONCURRENT_BROWSERS=2

# Aggressive (only for your own content)
MIN_DOMAIN_DELAY=5
MAX_CONCURRENT_BROWSERS=4
```

## Production Deployment Guide

### 1. Proxy Support (Recommended for High-Volume)

For serious stealth, rotate through residential proxies:

```python
# Configure proxies.txt with your proxy list
# GhostFetch will automatically rotate and track health.
```

**Recommended proxy providers:**
- BrightData (datacenter/residential)
- ScrapingBee (cloud-based)
- Oxylabs (residential networks)
- Local proxy rotation with tools like `scrapy-proxy-pool`

### 2. Caching Layer (Reduce Redundant Requests)

For repeated fetches, implement Redis caching:

```python
import redis

cache = redis.Redis(host='localhost', port=6379)

async def fetch_with_cache(url, ttl=3600):
    cached = cache.get(url)
    if cached:
        return json.loads(cached)
    
    result = await scraper.fetch(url)
    cache.setex(url, ttl, json.dumps(result))
    return result
```

**Docker Compose with Redis:**
```yaml
services:
  ghostfetch:
    build: .
    ports:
      - "8000:8000"
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### 3. Security & Authentication

Add API key authentication before exposing publicly:

```python
from fastapi import Header, HTTPException

VALID_API_KEYS = set(os.getenv("API_KEYS", "").split(","))

@app.post("/fetch")
async def fetch_endpoint(request: FetchRequest, x_api_key: str = Header(None)):
    if not x_api_key or x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # ... rest of endpoint
```

Usage:
```bash
curl -X POST "http://localhost:8000/fetch" \
     -H "x-api-key: your-secret-key" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'
```

### 4. Monitoring & Observability

**Log rotation** (automatically configured):
- Logs stored in `storage/scraper.log`
- Max 5MB per file, keeps 5 backups
- Check for errors: `tail -f storage/scraper.log | grep ERROR`

**Database queries for analytics:**
```bash
sqlite3 storage/jobs.db "SELECT status, COUNT(*) FROM jobs GROUP BY status;"
```

**Health check monitoring:**
```bash
while true; do
  curl http://localhost:8000/health | jq .
  sleep 30
done
```

### 5. Model Context Protocol (MCP)

GhostFetch includes an MCP server for integration with Claude Desktop and other MCP-aware agents.

Configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "ghostfetch": {
      "command": "python",
      "args": ["-m", "ghostfetch.mcp_server"],
      "env": {
        "SYNC_TIMEOUT_DEFAULT": "120"
      }
    }
  }
}
```

This exposes a `ghostfetch` tool to the agent:
- `url`: The URL to fetch
- `context_id`: Optional session ID
- `timeout`: Optional timeout (seconds)

## Performance & Monitoring

### Logging
Logs are written to `storage/scraper.log` with rotation (5MB max):
- Stream output to console (INFO level)
- File output with detailed format

### Load Testing
Run included load tests:
```bash
# Python async load test
python scripts/load_test.py
```

### Database
Job history is stored in `storage/jobs.db` (SQLite):
- Persistent across restarts
- Automatic cleanup of old jobs (configurable TTL)
- Query jobs directly for analytics/debugging

## Troubleshooting

**Playwright Error: Executable doesn't exist**
If you see an error about the browser executable not being found, run:
```bash
playwright install chromium
```

**Timeout Errors**
If fetching times out, it might be due to slow network or heavy anti-bot protections. You can try:
- Increasing timeout in `src/core/scraper.py` (default is 60000ms)
- Increasing `MIN_DOMAIN_DELAY` to avoid rate-limiting

**Job Stuck in "Processing"**
Check logs in `storage/scraper.log` for errors. If stuck, restart the service.

**GitHub Comments Not Posting**
Ensure:
- `gh` CLI is installed: `brew install gh` (macOS) or `apt install gh` (Linux)
- You're authenticated: `gh auth login`
- `GITHUB_REPO` is set correctly
- `GITHUB_TOKEN` is in your environment

**High Memory Usage**
Reduce `MAX_CONCURRENT_BROWSERS` or `MAX_REQUESTS_PER_BROWSER` in configuration.

## Publishing Setup

### Docker Hub

To enable automated Docker image publishing:

1. Create a Docker Hub account and repository (`your-username/ghostfetch`)
2. Generate an access token at https://hub.docker.com/settings/security
3. Add these secrets to your GitHub repository:
   - `DOCKERHUB_USERNAME`: Your Docker Hub username
   - `DOCKERHUB_TOKEN`: Your access token

Images will be published automatically on pushes to `main` and version tags.

### PyPI (Trusted Publishing)

To enable automated PyPI publishing:

1. Go to https://pypi.org/manage/account/publishing/
2. Add a new pending publisher:
   - **PyPI Project Name**: `ghostfetch`
   - **Owner**: `iArsalanshah`
   - **Repository**: `GhostFetch`
   - **Workflow name**: `pypi-publish.yml`
   - **Environment**: `pypi`
3. Create a GitHub Release to trigger publishing

No API tokens needed - uses OIDC trusted publishing.


## Legal Disclaimer

GhostFetch is provided for educational and research purposes only. Users are solely responsible for ensuring their use complies with:
1. The Terms of Service of target websites
2. Applicable laws regarding data access and automation (including CFAA in the US)
3. The robots.txt and scraping policies of target domains

This tool should not be used to:
- Scrape private or authenticated content without authorization
- Circumvent security measures on sites where such circumvention violates applicable law
- Violate the Terms of Service of social media platforms (including X/Twitter)


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=iArsalanshah/GhostFetch&type=Date)](https://star-history.com/#iArsalanshah/GhostFetch&Date)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
