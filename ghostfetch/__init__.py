"""
GhostFetch - A stealthy headless browser service for AI agents.
Bypasses anti-bot protections to fetch content and convert to clean Markdown.
"""

__version__ = "2026.2.5"

from ghostfetch.fetch import fetch, fetch_async, fetch_markdown
from ghostfetch.client import GhostFetchClient

__all__ = [
    "fetch", 
    "fetch_async", 
    "fetch_markdown",
    "GhostFetchClient", 
    "__version__"
]
