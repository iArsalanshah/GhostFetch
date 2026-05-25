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
from urllib.parse import urlparse
from src.auth_session import auth_session_store
from src.utils.security import URLValidationError

# Add parent directory to path so we can import src modules
_package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _package_dir not in sys.path:
    sys.path.insert(0, _package_dir)


async def fetch_async(
    url: str,
    context_id: Optional[str] = None,
    auth_session_id: Optional[str] = None,
    timeout: float = 120.0,
) -> Dict[str, Any]:
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
    auth_storage_state_path = None
    if auth_session_id:
        session = auth_session_store.get_session(auth_session_id)
        host = (urlparse(url).hostname or "").lower().rstrip(".")
        if host != session.domain and not host.endswith(f".{session.domain}"):
            raise URLValidationError("URL host does not match auth session domain")
        auth_session_store.mark_used(auth_session_id)
        auth_storage_state_path = session.storage_state_path
    
    scraper = StealthScraper()
    try:
        result = await asyncio.wait_for(
            scraper.fetch(url, context_id=context_id, auth_storage_state_path=auth_storage_state_path),
            timeout=timeout
        )
        if not result:
            return {"metadata": {}, "markdown": "", "url": url, "status": "empty"}
        return {
            "metadata": result.get("metadata", {}),
            "markdown": result.get("markdown", ""),
            "url": url,
            "status": "success",
        }
    finally:
        await scraper.stop()


def fetch(
    url: str,
    context_id: Optional[str] = None,
    auth_session_id: Optional[str] = None,
    timeout: float = 120.0,
) -> Dict[str, Any]:
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
    return asyncio.run(fetch_async(url, context_id=context_id, auth_session_id=auth_session_id, timeout=timeout))


def fetch_markdown(
    url: str,
    context_id: Optional[str] = None,
    auth_session_id: Optional[str] = None,
    timeout: float = 120.0,
) -> str:
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
    result = fetch(url, context_id=context_id, auth_session_id=auth_session_id, timeout=timeout)
    return result.get("markdown", "")
