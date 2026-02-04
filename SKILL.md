---
name: ghostfetch
description: Stealthy web fetcher that bypasses anti-bot protections. Fetches content from sites like X.com and converts to clean Markdown for AI agents.
version: 1.0.0
author: iArsalanshah
tags:
  - web-scraping
  - stealth
  - markdown
  - browser-automation
  - anti-bot-bypass
---

# GhostFetch Skill

Fetch web content from sites that block AI agents. Uses a stealthy headless browser with advanced fingerprinting to bypass anti-bot protections and returns clean Markdown.

## When to Use

- Fetching content from X.com/Twitter posts
- Reading articles from sites that block bots
- Extracting content from JavaScript-heavy sites
- Getting clean Markdown from any webpage for LLM consumption

## Prerequisites

GhostFetch must be running as a service. Start it with:

```bash
# Option 1: If installed via pip
ghostfetch serve

# Option 2: Docker
docker run -p 8000:8000 iarsalanshah/ghostfetch
```

## Usage

### Synchronous Fetch (Recommended)

Use the `/fetch/sync` endpoint for simple, blocking requests:

```bash
curl "http://localhost:8000/fetch/sync?url=https://example.com"
```

### Python

```python
import requests

def ghostfetch(url: str, timeout: float = 120.0) -> dict:
    """
    Fetch content from a URL using GhostFetch.
    
    Returns:
        dict with 'metadata' and 'markdown' keys
    """
    response = requests.post(
        "http://localhost:8000/fetch/sync",
        json={"url": url, "timeout": timeout}
    )
    response.raise_for_status()
    return response.json()

# Example
result = ghostfetch("https://x.com/user/status/123")
print(result["markdown"])
```

### With SDK

```python
from ghostfetch import fetch

result = fetch("https://x.com/user/status/123")
print(result["metadata"]["title"])
print(result["markdown"])
```

## Response Format

```json
{
  "metadata": {
    "title": "Page Title",
    "author": "Author Name",
    "publish_date": "2024-01-15",
    "images": ["https://example.com/image.jpg"]
  },
  "markdown": "# Page Title\n\nPage content in clean Markdown..."
}
```

## API Reference

### POST /fetch/sync

Synchronous fetch - blocks until content is ready.

**Request:**
```json
{
  "url": "https://example.com",
  "context_id": "optional-session-id",
  "timeout": 120
}
```

**Response:** See Response Format above.

### GET /fetch/sync

Same as POST but via query parameters:

```
GET /fetch/sync?url=https://example.com&timeout=60
```

### POST /fetch

Async fetch - returns job ID immediately, poll for results.

**Request:**
```json
{
  "url": "https://example.com",
  "callback_url": "https://your-webhook.com/callback",
  "github_issue": 42
}
```

**Response:**
```json
{
  "job_id": "abc123",
  "url": "https://example.com",
  "status": "queued"
}
```

### GET /job/{job_id}

Check job status and get results.

### GET /health

Health check endpoint.

## Configuration

Set via environment variables when running the service:

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNC_TIMEOUT_DEFAULT` | 120 | Default timeout for sync requests (seconds) |
| `MAX_SYNC_TIMEOUT` | 300 | Maximum allowed timeout |
| `MAX_CONCURRENT_BROWSERS` | 2 | Concurrent browser contexts |
| `MIN_DOMAIN_DELAY` | 10 | Seconds between requests to same domain |

## Error Handling

| Status Code | Meaning |
|-------------|---------|
| 200 | Success |
| 400 | Invalid request (non-retryable error) |
| 502 | Fetch failed (retryable) |
| 504 | Request timeout |

## Tips

1. **Use context_id for multi-step workflows** - Sessions are persisted per context, maintaining cookies between requests.

2. **Respect rate limits** - GhostFetch has built-in domain delays. Don't bypass these.

3. **Check metadata first** - The structured metadata often has what you need without parsing Markdown.

## Related Skills

- `browser` - General browser automation
- `web_fetch` - Simple HTTP fetching (for non-protected sites)
