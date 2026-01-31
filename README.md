# GhostFetch

A stealthy headless browser service for AI agents. Bypasses anti-bot protections to fetch content from sites like X.com and converts it to clean Markdown.

## Features
- **Stealth Browsing**: Uses Playwright with custom flags and user-agent rotation to mimic human users.
- **Markdown Output**: Automatically converts HTML to Markdown for easy consumption by LLMs.
- **X.com Support**: Logic to wait for dynamic content on Twitter/X.
- **Dual Mode**: Can be used as a CLI tool or a REST API service.

## Project Structure

```
stealth-fetcher/
├── main.py           # FastAPI service entry point
├── scraper.py        # Core scraping logic and CLI implementation
├── requirements.txt  # Python dependencies
├── LICENSE           # MIT License
└── README.md         # This documentation
```

## Installation

1.  **Clone/Navigate** to the directory:
    ```bash
    cd stealth-fetcher
    ```

2.  **Install Dependencies**:
    ```bash
    # Create a virtual environment (optional but recommended)
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

    # Install python packages
    pip install -r requirements.txt

    # Install browser binaries
    playwright install chromium
    ```

## Usage

### 1. CLI Mode (Direct Fetch)
Use calls this tool directly from the command line to fetch a page.

```bash
python scraper.py "https://x.com/mrnacknack/status/2016134416897360212"
```

### 2. API Mode (Service for Agents)
Run the server to expose a fetching endpoint for other agents.

```bash
python main.py
```
The server will start at `http://localhost:8000`.

**API Endpoint:**
- **POST** `/fetch`
- **Body**: `{"url": "https://example.com"}`

**Example Request:**
```bash
curl -X POST "http://localhost:8000/fetch" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://x.com/mrnacknack/status/2016134416897360212"}'
```

## Integration with AI Agents
Your agent can simply make an HTTP POST request to the API server when it encounters a blocked URL.

```python
import requests

def fetch_blocked_content(url):
    response = requests.post("http://localhost:8000/fetch", json={"url": url})
    if response.status_code == 200:
        return response.json()["markdown"]
    else:
        return "Error fetching content"
```

## Configuration

The `scraper.py` file contains a configurable list of user agents to rotate through. You can add more user agents to the `USER_AGENTS` list to further enhance stealth.

```python
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    # Add more here
]
```

## Specific Handling
- **X/Twitter**: The scraper waits for `[data-testid="tweetText"]` to ensure the tweet content is loaded before capturing.

## Troubleshooting

**Playwright Error: Executable doesn't exist**
If you see an error about the browser executable not being found, run:
```bash
playwright install chromium
```

**Timeout Errors**
If fetching times out, it might be due to slow network or heavy anti-bot protections. You can try increasing the timeout in `scraper.py` (default is 60000ms).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
