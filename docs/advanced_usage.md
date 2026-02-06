# Advanced Usage & Deployment

This guide covers advanced configurations, integrations, and production deployment strategies for GhostFetch.

## GitHub Integration

GhostFetch can automatically post fetch results as comments on GitHub issues. This is useful for agents that manage tasks via GitHub.

### Usage
Add the `github_issue` parameter to your request:

```bash
curl -X POST "http://localhost:8000/fetch" \
     -H "Content-Type: application/json" \
     -d '{
           "url": "https://example.com",
           "github_issue": 42
         }'
```

*Result will be posted as a comment on issue #42 of the configured repository.*

### Requirements
1.  **GitHub CLI (`gh`)**: Must be installed on the server (`brew install gh` or `apt install gh`).
2.  **Authentication**: Run `gh auth login` on the server.
3.  **Environment Variables**:
    *   `GITHUB_REPO`: The `owner/repo` to post to (e.g., `iArsalanshah/GhostFetch`).
    *   `GITHUB_TOKEN`: (Optional) Auth token if not logged in via CLI.

---

## Model Context Protocol (MCP)

GhostFetch includes an MCP server for integration with Claude Desktop and other MCP-aware agents.

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

## Production Deployment

### Docker Recommended Setup

For high-volume scraping, we recommend using Docker Compose with environment variables.

Create a `.env` file:
```bash
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
