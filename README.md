![GhostFetch Banner](docs/banner.png)

# GhostFetch

[![PyPI version](https://img.shields.io/pypi/v/ghostfetch?color=blue)](https://pypi.org/project/ghostfetch/)
[![Docker Hub](https://img.shields.io/docker/pulls/iarsalanshah/ghostfetch)](https://hub.docker.com/r/iarsalanshah/ghostfetch)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Fetch the unfetchable.** A stealthy, headless browser service for AI agents.

GhostFetch bypasses anti-bot protections to fetch content from difficult sites (like X.com and LinkedIn) and converts it into clean, LLM-ready Markdown. It handles the complexity of headless browsing, proxy rotation, and fingerprinting so your agent doesn't have to.

*Powered by the 🦊 Phantom Fox — slipping past every wall, unseen.*

## Why GhostFetch?

Fetching content for AI agents is hard. Simple `requests` or `curl` calls fail on modern sites due to JavaScript rendering and anti-bot checks. Heavy browser automation tools are slow and complex to manage.

GhostFetch solves this by providing:
*   🦊 **Stealth by Design**: "Ghost Protocol" fingerprinting to mimic real users.
*   📜 **LLM-Native Output**: Returns clean Markdown, not messy HTML.
*   📜 **Smart Scrolling**: Automatically expands infinite feeds (perfect for X/Twitter threads).
*   🔐 **Authenticated Sessions**: Bypass login walls for LinkedIn, X/Twitter, and other gated sites.
*   ⚡ **Zero-Config**: Browsers auto-install and manage themselves.

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

### 3. Fetch Behind a Login Wall (LinkedIn, etc.)
```bash
# Open a visible browser to log in — session is saved for reuse
ghostfetch auth login --domain linkedin.com --login-url https://www.linkedin.com/login

# Fetch content using the saved session
ghostfetch "https://www.linkedin.com/in/profile" --auth-session-id <SESSION_ID>
```

---

## ✨ Features

*   ⚡ **Synchronous & Async API**: Flexible integration patterns.
*   🦊 **Ghost Protocol**: Advanced proxy rotation and cohesive browser fingerprinting.
*   📜 **Smart Scrolling**: Auto-detects and scrolls infinite feeds to capture full content.
*   🐦 **X.com Optimized**: Special handling for Twitter/X hydration and thread expansion.
*   🔍 **Metadata Extraction**: Auto-extracts title, author, date, and images.
*   📬 **Job Queue**: Built-in async job system with webhooks and retries.
*   🍪 **Persistent Sessions**: Cookie/localStorage persistence per domain.
*   🔐 **Authenticated Sessions**: Domain-locked session management for login-gated pages (LinkedIn, X, etc.).
*   🐳 **Docker Ready**: Production-ready container images included.

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

# Fetch behind a login wall
ghostfetch "https://linkedin.com/in/profile" --auth-session-id abc123

# Manage authenticated sessions
ghostfetch auth login --domain linkedin.com
ghostfetch auth status
ghostfetch auth revoke <SESSION_ID>
```

### Python SDK
```python
from ghostfetch import fetch

# Simple fetch
result = fetch("https://example.com")
print(result['markdown'])

# Fetch behind a login wall
result = fetch("https://linkedin.com/in/profile", auth_session_id="abc123")
print(result['markdown'])
```

### REST API

Start the server:
```bash
ghostfetch serve
```

By default, fetch endpoints require API key auth:
```bash
export GHOSTFETCH_API_KEY="replace-with-strong-token"
```

**Synchronous Fetch (Blocks until done):**
```bash
curl -H "X-API-Key: $GHOSTFETCH_API_KEY" \
  "http://localhost:8000/fetch/sync?url=https://example.com"
```

**Asynchronous Fetch (Background Job):**
```bash
curl -X POST "http://localhost:8000/fetch" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $GHOSTFETCH_API_KEY" \
     -d '{"url": "https://example.com", "callback_url": "https://yourapp.com/webhook"}'
```

**Fetch with Authenticated Session:**
```bash
curl -X POST "http://localhost:8000/fetch/sync" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $GHOSTFETCH_API_KEY" \
     -d '{"url": "https://linkedin.com/in/profile", "auth_session_id": "abc123"}'
```

**Import an Auth Session (programmatic):**
```bash
curl -X POST "http://localhost:8000/auth/sessions/import" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $GHOSTFETCH_API_KEY" \
     -d '{"domain": "linkedin.com", "storage_state": {...}, "ttl_seconds": 86400}'
```

**List Auth Sessions:**
```bash
curl -H "X-API-Key: $GHOSTFETCH_API_KEY" \
  "http://localhost:8000/auth/sessions"
```

**Revoke an Auth Session:**
```bash
curl -X DELETE "http://localhost:8000/auth/sessions/abc123" \
  -H "X-API-Key: $GHOSTFETCH_API_KEY"
```

**Check Health:**
```bash
curl "http://localhost:8000/health"
```

**Check Job Status:**
```bash
curl -H "X-API-Key: $GHOSTFETCH_API_KEY" \
  "http://localhost:8000/job/a1b2c3d4-e5f6-7890"
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

**Auth Wall Detection:** When fetching login-gated pages without a valid session, the response status will be one of:
*   `auth_required` — The page requires a login.
*   `auth_expired` — The saved session has expired.
*   `auth_challenge` — An additional security challenge (e.g., CAPTCHA) was encountered.

---

## 📊 Configuration

GhostFetch is configured via environment variables.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MAX_CONCURRENT_BROWSERS` | `2` | Max concurrent browser contexts |
| `MIN_DOMAIN_DELAY` | `30` | Seconds between requests to same domain |
| `JITTER_MIN` | `3.0` | Minimum random wait time after page load |
| `JITTER_MAX` | `7.0` | Maximum random wait time after page load |
| `GHOSTFETCH_PORT` | `8000` | Port for the API server |
| `PROXY_STRATEGY` | `round_robin` | `round_robin` or `random` |
| `GHOSTFETCH_API_KEY` | _empty_ | Required API key for fetch endpoints when auth is enabled |
| `REQUIRE_API_KEY` | `true` | Enable `X-API-Key` enforcement on fetch endpoints |
| `BLOCK_PRIVATE_NETWORKS` | `true` | Blocks localhost/private IP targets to reduce SSRF risk |
| `CALLBACK_ALLOWED_HOSTS` | _empty_ | Optional comma-separated callback host allowlist |
| `CALLBACK_MAX_ATTEMPTS` | `3` | Max retries for webhook callback delivery |
| `CALLBACK_RETRY_BASE_SECONDS` | `1.0` | Base delay used for exponential callback retry |
| `GITHUB_TOKEN` | _empty_ | Token used for posting GitHub issue comments via API |
| `LOG_FORMAT` | `text` | Set to `json` for structured logs |
| `GHOSTFETCH_DEBUG` | `false` | Enables development reload mode when running `python main.py` |
| `STORAGE_DIR` | `storage` | Directory for persistent sessions, auth sessions, and logs |

**Proxies:**
Create a `proxies.txt` file in the working directory with one proxy per line:
`http://user:pass@host:port`

Concurrency note:
`MAX_CONCURRENT_BROWSERS` is a global browser-context cap shared by both sync and async fetch paths.

Auth session storage note:
Authenticated session state files are stored under `STORAGE_DIR/auth_sessions/` and may contain sensitive cookies. Keep `STORAGE_DIR` on a private filesystem with restricted access.

---

## 📈 Advanced Usage

For GitHub integration, MCP Server configuration (Claude Desktop), and production deployment guides (Docker Compose, Proxy strategies), please see:

👉 **[Advanced Usage & Deployment Guide](docs/advanced_usage.md)**

---

## 🤖 Agent Plugins Integration

GhostFetch is packaged as a portable **Agent Plugin** conforming to the open, vendor-neutral [Agent Plugins 1.0.0](https://agent-plugins.org) standard. Any conformant agent client (Cursor, Claude Code, OpenAI Codex, etc.) can discover and load GhostFetch as a plugin.

### Plugin Structure

The plugin consists of two manifest files at the repository root:

- **`plugin.json`** — The Agent Plugins manifest declaring the plugin metadata (name, version, author, license, keywords).
- **`mcp.json`** — The MCP server connection configuration in Agent Plugins format.

Additionally, the plugin includes:
- **`skills/ghostfetch/SKILL.md`** — An Agent Skill (per the [Agent Skills specification](https://agentskills.io/specification)) that teaches agents how to use GhostFetch.

### Loading the Plugin

Conformant agent clients can load GhostFetch by pointing to this repository:

```bash
# Example: clone and install as a plugin
git clone https://github.com/iArsalanshah/GhostFetch.git
# The client reads plugin.json + mcp.json to discover capabilities
```

The `mcp.json` declares a single MCP server `ghostfetch` that runs via stdio:
- **Command:** `python -m ghostfetch.mcp_server`
- **Environment:** `SYNC_TIMEOUT_DEFAULT=120`, `MAX_SYNC_TIMEOUT=300`

### Standalone MCP Server

You can also run the MCP server directly without a plugin client:

```bash
# Start the MCP server (stdio transport)
python -m ghostfetch.mcp_server

# Or with custom timeouts
SYNC_TIMEOUT_DEFAULT=60 MAX_SYNC_TIMEOUT=180 python -m ghostfetch.mcp_server
```

The server exposes GhostFetch's fetching capabilities as MCP tools that any MCP-compatible client can invoke.

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
