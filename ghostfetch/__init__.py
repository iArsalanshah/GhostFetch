"""
GhostFetch - A stealthy headless browser service for AI agents.
Bypasses anti-bot protections to fetch content and convert to clean Markdown.
"""

__version__ = "1.0.0"

from ghostfetch.fetch import fetch, fetch_async
from ghostfetch.client import GhostFetchClient

__all__ = ["fetch", "fetch_async", "GhostFetchClient", "__version__"]
