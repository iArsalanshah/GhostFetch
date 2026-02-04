"""
GhostFetch - Simple fetch functions for AI agents.

Usage:
    from ghostfetch import fetch
    content = fetch("https://x.com/user/status/123")
    print(content["markdown"])
"""

import asyncio
import sys
import os
from typing import Optional, Dict, Any

# Add parent directory to path so we can import src modules
_package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _package_dir not in sys.path:
    sys.path.insert(0, _package_dir)


async def fetch_async(url: str, context_id: Optional[str] = None, timeout: float = 120.0) -> Dict[str, Any]:
    """
    Fetch a URL asynchronously and return structured content.
    
    Args:
        url: The URL to fetch
        context_id: Optional context ID for session persistence
        timeout: Maximum time to wait for the fetch (default: 120s)
    
    Returns:
        dict with keys:
            - metadata: dict with title, author, publish_date, images
            - markdown: string with the page content as markdown
    
    Example:
        import asyncio
        from ghostfetch import fetch_async
        
        async def main():
            result = await fetch_async("https://example.com")
            print(result["markdown"])
        
        asyncio.run(main())
    """
    from src.core.scraper import StealthScraper
    
    scraper = StealthScraper()
    try:
        result = await asyncio.wait_for(
            scraper.fetch(url, context_id=context_id),
            timeout=timeout
        )
        return result if result else {"metadata": {}, "markdown": ""}
    finally:
        await scraper.stop()


def fetch(url: str, context_id: Optional[str] = None, timeout: float = 120.0) -> Dict[str, Any]:
    """
    Fetch a URL synchronously and return structured content.
    
    This is the simplest way to use GhostFetch - one function call, get content.
    
    Args:
        url: The URL to fetch
        context_id: Optional context ID for session persistence
        timeout: Maximum time to wait for the fetch (default: 120s)
    
    Returns:
        dict with keys:
            - metadata: dict with title, author, publish_date, images
            - markdown: string with the page content as markdown
    
    Example:
        from ghostfetch import fetch
        
        result = fetch("https://x.com/user/status/123")
        print(result["metadata"]["title"])
        print(result["markdown"])
    """
    return asyncio.run(fetch_async(url, context_id=context_id, timeout=timeout))


def fetch_markdown(url: str, context_id: Optional[str] = None, timeout: float = 120.0) -> str:
    """
    Fetch a URL and return only the markdown content.
    
    Args:
        url: The URL to fetch
        context_id: Optional context ID for session persistence  
        timeout: Maximum time to wait for the fetch (default: 120s)
    
    Returns:
        str: The page content as markdown
    
    Example:
        from ghostfetch import fetch_markdown
        
        markdown = fetch_markdown("https://example.com")
        print(markdown)
    """
    result = fetch(url, context_id=context_id, timeout=timeout)
    return result.get("markdown", "")
