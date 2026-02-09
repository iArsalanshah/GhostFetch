---
name: ghostfetch
description: Stealthy web fetching for AI agents. Bypasses blocks on X.com and other sites to return clean Markdown.
homepage: https://github.com/iArsalanshah/GhostFetch
metadata:
  openclaw:
    emoji: "👻"
    requires:
      bins:
        - python3
---

# GhostFetch

GhostFetch is a stealthy headless browser service designed specifically for AI agents. It bypasses anti-bot protections (like those on X/Twitter) and returns clean, LLM-friendly Markdown.

## Installation

GhostFetch is already in your workspace at the repo root. To use it as a skill, ensure the Python environment is set up from the repo directory:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

You can use GhostFetch in two ways:

### 1. Direct CLI (Recommended for quick fetches)
Use the scraper module directly to get Markdown from a URL.

```bash
python3 -m src.core.scraper "https://x.com/user/status/123"
```

### 2. API Mode (Background service)
Start the FastAPI server to handle concurrent jobs and webhooks.

```bash
# Start server
python3 main.py

# Fetch via API
curl -X POST "http://localhost:8000/fetch" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://x.com/user/status/123"}'
```

## Stealth Features
- **Ghost Protocol**: Advanced proxy rotation and hardware fingerprinting.
- **X.com Optimized**: Specific logic to wait for dynamic tweet content.
- **LLM Ready**: Automatic HTML-to-Markdown conversion.

---
*Created by Syed Arsalan Shah (@iArsalanshah)*
