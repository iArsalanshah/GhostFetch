# Advanced Usage & Deployment

This guide covers advanced configurations, integrations, and production deployment strategies for GhostFetch.

## GitHub Integration

GhostFetch can automatically post fetch results as comments on GitHub issues. This is useful for agents that manage tasks via GitHub.

### Usage
Add the `github_issue` parameter to your request:

```bash
curl -X POST "http://localhost:8000/fetch" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $GHOSTFETCH_API_KEY" \
     -d '{
           "url": "https://example.com",
           "github_issue": 42
         }'
```

*Result will be posted as a comment on issue #42 of the configured repository.*

### Requirements
1.  **Environment Variables**:
    *   `GITHUB_REPO`: The `owner/repo` to post to (e.g., `iArsalanshah/GhostFetch`).
    *   `GITHUB_TOKEN`: Required token with issue comment permissions.

---

## Model Context Protocol (MCP)

GhostFetch includes an MCP server for integration with Claude Desktop and other MCP-aware agents.

GhostFetch is also packaged as a portable **Agent Plugin** conforming to the open [Agent Plugins 1.0.0](https://agent-plugins.org) standard. Conformant agent clients (Cursor, Claude Code, OpenAI Codex, etc.) can load the plugin directly from the repo root via `plugin.json` + `mcp.json`, and an Agent Skill (`skills/ghostfetch/SKILL.md`) teaches agents how to use it. See the README's "Agent Plugins Integration" section for details. The root `mcp.json` is the Agent Plugins-format equivalent of the raw client config below.

### Configuration (`claude_desktop_config.json`)

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
- `context_id`: Session ID (optional)
- `timeout`: Timeout in seconds (optional)

---

## 🔐 Authenticated Sessions

GhostFetch can fetch content behind login walls (LinkedIn, X/Twitter, private forums) using **domain-locked authenticated sessions**. Sessions are saved Playwright browser storage states, bound to a specific domain, and expire automatically via TTL.

### CLI Workflow

The easiest way to create a session is via the interactive CLI login:

```bash
# Opens a visible browser for manual login — session is saved for reuse
ghostfetch auth login --domain linkedin.com --login-url https://www.linkedin.com/login

# Fetch content using the saved session
ghostfetch "https://www.linkedin.com/in/profile" --auth-session-id <SESSION_ID>

# List active sessions
ghostfetch auth status

# Revoke a session
ghostfetch auth revoke <SESSION_ID>
```

### REST API Workflow

**Import a session programmatically** (e.g., from an existing Playwright storage state):
```bash
curl -X POST "http://localhost:8000/auth/sessions/import" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $GHOSTFETCH_API_KEY" \
     -d '{
       "domain": "linkedin.com",
       "storage_state": { "cookies": [...], "origins": [...] },
       "session_id": "my-linkedin-session",
       "ttl_seconds": 86400
     }'
```

**Fetch with a session:**
```bash
curl -X POST "http://localhost:8000/fetch/sync" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $GHOSTFETCH_API_KEY" \
     -d '{
       "url": "https://www.linkedin.com/in/profile",
       "auth_session_id": "my-linkedin-session"
     }'
```

**List and revoke sessions:**
```bash
curl -H "X-API-Key: $GHOSTFETCH_API_KEY" "http://localhost:8000/auth/sessions"
curl -X DELETE "http://localhost:8000/auth/sessions/my-linkedin-session" \
  -H "X-API-Key: $GHOSTFETCH_API_KEY"
```

### Python SDK Workflow

```python
from ghostfetch import fetch, GhostFetchClient

# Using the simple fetch function
result = fetch("https://linkedin.com/in/profile", auth_session_id="my-linkedin-session")
print(result["markdown"])

# Using the GhostFetchClient
client = GhostFetchClient("http://localhost:8000", api_key="your-api-key")

# Import a session from an existing storage state
client.import_auth_session(
    domain="linkedin.com",
    storage_state={"cookies": [...], "origins": [...]},
    session_id="my-linkedin-session",
    ttl_seconds=86400,
)

# Fetch with the session
result = client.fetch_sync(
    "https://linkedin.com/in/profile",
    auth_session_id="my-linkedin-session",
)
print(result["markdown"])
```

### Domain Binding

Sessions are **locked to their auth domain**. If you create a session for `linkedin.com`, GhostFetch will reject attempts to use it for `x.com`. This prevents accidental credential leakage across unrelated sites.

### Auth Wall Detection

When fetching a login-gated page without a valid session, GhostFetch returns structured status codes instead of garbage markup:

| Status | Meaning |
| :--- | :--- |
| `auth_required` | The page requires a login. |
| `auth_expired` | The saved session has expired or been invalidated. |
| `auth_challenge` | An additional security challenge (e.g., CAPTCHA, 2FA) was encountered. |

### Security Notes

*   Auth endpoints require API key authentication (`REQUIRE_API_KEY=true`).
*   Session files are stored under `STORAGE_DIR/auth_sessions/` and may contain sensitive cookies. Keep `STORAGE_DIR` on a private filesystem with restricted access.
*   Sessions are validated against `BLOCK_PRIVATE_NETWORKS` — you cannot use auth sessions to reach internal IPs.

---

## Production Deployment

### Docker Recommended Setup

For high-volume scraping, we recommend using Docker Compose with environment variables.

Create a `.env` file:
```bash
GHOSTFETCH_API_KEY=replace-with-strong-token
GITHUB_TOKEN=ghp_your_token
MAX_CONCURRENT_BROWSERS=4
MIN_DOMAIN_DELAY=5
GITHUB_REPO=your-org/your-repo
JOB_TTL_SECONDS=86400
```

Run with compose:
```bash
docker-compose --env-file .env up -d
```

### Proxy Configuration (Critical)

For serious stealth and to avoid rate limits, you **must** use proxies.

1.  Create a `proxies.txt` file in your working directory (or mount it to `/app/proxies.txt` in Docker).
2.  Add one proxy per line:
    ```
    http://user:pass@1.2.3.4:8080
    http://user:pass@5.6.7.8:8080
    ```
3.  Set `PROXY_STRATEGY=round_robin` (default) or `random`.

### Monitoring

*   **Logs**: Check `storage/scraper.log` for errors.
*   **Health Check**: Poll `GET /health` to monitor browser status and queue depth.
