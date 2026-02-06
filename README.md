# GhostFetch

[![PyPI version](https://img.shields.io/pypi/v/ghostfetch?color=blue)](https://pypi.org/project/ghostfetch/)
[![Docker Hub](https://img.shields.io/docker/pulls/iarsalanshah/ghostfetch)](https://hub.docker.com/r/iarsalanshah/ghostfetch)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A stealthy, headless browser service for AI agents.**

GhostFetch bypasses anti-bot protections to fetch content from difficult sites (like X.com) and converts it into clean, LLM-ready Markdown. It handles the complexity of headless browsing, proxy rotation, and fingerprinting so your agent doesn't have to.

## Why GhostFetch?

Fetching content for AI agents is hard. Simple `requests` or `curl` calls fail on modern sites due to JavaScript rendering and anti-bot checks. Heavy browser automation tools are slow and complex to manage.

GhostFetch solves this by providing:
*   **Stealth by Design**: "Ghost Protocol" fingerprinting to mimic real users.
*   **LLM-Native Output**: Returns clean Markdown, not messy HTML.
*   **Smart Scrolling**: Automatically expands infinite feeds (perfect for X/Twitter threads).
*   **Zero-Config**: Browsers auto-install and manage themselves.

### Architecture

`URL` → **GhostFetch** (Headless Browser + Ghost Protocol) → **Markdown** → `AI Agent`

---

## 🚀 Quick Start

The fastest way to get started is via pip.

### 1. Install
```bash
pip install ghostfetch
```

### 2. Fetch a URL
Browsers will auto-install on the first run.
```bash
ghostfetch "https://x.com/user/status/123"
```

**Output:**
```json
{
  "metadata": { "title": "...", "author": "..." },
  "markdown": "Captured content in markdown format..."
}
```

---

## ✨ Features

*   **Synchronous & Async API**: Flexible integration patterns.
*   **Ghost Protocol**: Advanced proxy rotation and cohesive browser fingerprinting.
*   **Smart Scrolling**: Auto-detects and scrolls infinite feeds to capture full content.
*   **X.com Optimized**: Special handling for Twitter/X hydration and thread expansion.
*   **Metadata Extraction**: Auto-extracts title, author, date, and images.
*   **Job Queue**: Built-in async job system with webhooks and retries.
*   **Persistent Sessions**: Cookie/localStorage persistence per domain.
*   **Docker Ready**: Production-ready container images included.

---

## 📦 Installation

### Option 1: Python Package (Best for Agents)

```bash
pip install ghostfetch
# Usage:
# ghostfetch "url"             (CLI)
# from ghostfetch import fetch (Python SDK)
```

### Option 2: Docker (Best for Services)

```bash
docker run -p 8000:8000 iarsalanshah/ghostfetch
# Service available at http://localhost:8000
```

### Option 3: Manual / Source

```bash
git clone https://github.com/iArsalanshah/GhostFetch.git
cd GhostFetch
pip install -e .
playwright install chromium
```

---

## 🧰 Usage

### CLI
```bash
# JSON output for parsing
ghostfetch "https://example.com" --json

# Metadata only
ghostfetch "https://example.com" --metadata-only
```

### Python SDK
```python
from ghostfetch import fetch

result = fetch("https://example.com")
print(result['markdown'])
```

### REST API

Start the server:
```bash
ghostfetch serve
```

**Synchronous Fetch (Blocks until done):**
```bash
curl "http://localhost:8000/fetch/sync?url=https://example.com"
```

**Asynchronous Fetch (Background Job):**
```bash
curl -X POST "http://localhost:8000/fetch" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com", "callback_url": "https://yourapp.com/webhook"}'
```

**Check Health:**
```bash
curl "http://localhost:8000/health"
```

**Check Job Status:**
```bash
curl "http://localhost:8000/job/a1b2c3d4-e5f6-7890"
```

### Response Format
All successful fetches return a standardized JSON structure:
```json
{
  "metadata": {
    "title": "Page Title",
    "author": "Author Name",
    "publish_date": "2023-01-01",
    "images": ["image_url.jpg"]
  },
  "markdown": "# Page Title\n\nExtracted content...",
  "url": "https://example.com/original-url",
  "status": "success"
}
```

---

## 📊 Configuration

GhostFetch is configured via environment variables.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MAX_CONCURRENT_BROWSERS` | `2` | Max concurrent browser contexts |
| `MIN_DOMAIN_DELAY` | `10` | Seconds between requests to same domain |
| `GHOSTFETCH_PORT` | `8000` | Port for the API server |
| `PROXY_STRATEGY` | `round_robin` | `round_robin` or `random` |

**Proxies:**
Create a `proxies.txt` file in the working directory with one proxy per line:
`http://user:pass@host:port`

---

## 📈 Advanced Usage

For GitHub integration, MCP Server configuration (Claude Desktop), and production deployment guides (Docker Compose, Proxy strategies), please see:

👉 **[Advanced Usage & Deployment Guide](docs/advanced_usage.md)**

---

## 🛠 Troubleshooting

*   **Browser Executable Missing**: Run `playwright install chromium`.
*   **Timeouts**: Increase `timeout` in request or `SYNC_TIMEOUT_DEFAULT` env var.
*   **Memory Issues**: Reduce `MAX_CONCURRENT_BROWSERS`.

---

## 🤝 Contributing

PRs welcome. Open an issue for major changes.

---

## ⚠️ Legal Disclaimer

**For educational and research purposes only.**
Users are responsible for complying with the Terms of Service, robots.txt, and applicable laws of the websites they access. This tool should not be used for unauthorized scraping or circumventing security measures in violation of law.

---

## License
MIT License. See [LICENSE](LICENSE) for details.
