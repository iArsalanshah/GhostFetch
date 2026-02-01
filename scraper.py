import asyncio
import random
import sys
import logging
import time
from urllib.parse import urlparse
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import html2text
import os
from config import settings

from logging.handlers import RotatingFileHandler
import time

# Setup logging
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
log_path = os.path.join(settings.STORAGE_DIR, "scraper.log")
handler = RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=5)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(),
        handler
    ]
)
logger = logging.getLogger("GhostFetch")

class ScraperError(Exception):
    def __init__(self, message, error_code, retryable=False):
        self.message = message
        self.error_code = error_code
        self.retryable = retryable
        super().__init__(self.message)

# Common user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

class StealthScraper:
    def __init__(self):
        self.browser = None
        self.playwright = None
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_BROWSERS)
        self.restart_lock = asyncio.Lock()
        self.last_fetch = {} # {domain: timestamp}
        self.requests_count = 0

    async def start(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
        
        # Ensure storage directory exists
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)

        # Launch options for stealth
        if not self.browser or not self.browser.is_connected():
            logger.info("Launching new browser instance...")
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                    "--disable-dev-shm-usage",
                    "--disable-browser-side-navigation",
                    "--disable-gpu",
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                ]
            )

    async def stop(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def fetch(self, url: str):
        async with self.semaphore:
            async with self.restart_lock:
                self.requests_count += 1
                if self.requests_count > settings.MAX_REQUESTS_PER_BROWSER:
                    logger.info("Max requests reached for browser. Restarting...")
                    await self.stop()
                    self.requests_count = 1
                await self.start()

            # Domain-based storage state for cookie persistence
            domain = urlparse(url).netloc
            
            # Domain-level rate limiting
            now = time.time()
            if domain in self.last_fetch:
                elapsed = now - self.last_fetch[domain]
                if elapsed < settings.MIN_DOMAIN_DELAY:
                    wait_time = settings.MIN_DOMAIN_DELAY - elapsed
                    logger.info(f"Rate limiting {domain}: waiting {wait_time:.2f}s...")
                    await asyncio.sleep(wait_time)

            self.last_fetch[domain] = time.time()
            
            storage_path = os.path.join(settings.STORAGE_DIR, f"cookies_{domain}.json")
            
            context_kwargs = {
                "user_agent": random.choice(USER_AGENTS),
                "viewport": {"width": 1920, "height": 1080},
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "java_script_enabled": True,
            }

            if os.path.exists(storage_path):
                logger.debug(f"Loading session for {domain}...")
                context_kwargs["storage_state"] = storage_path

            context = await self.browser.new_context(**context_kwargs)

            # Basic stealth
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            """)

            page = await context.new_page()
            content = ""
            try:
                # Secure domain-only logging
                logger.info(f"Fetching {domain}...")
                
                # 60s timeout for page load
                try:
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    if not response:
                         raise ScraperError(f"No response from {domain}", "no_response", retryable=True)
                    
                    if response.status >= 400:
                        retryable = response.status in [408, 429, 500, 502, 503, 504]
                        raise ScraperError(f"HTTP {response.status} from {domain}", f"http_{response.status}", retryable=retryable)

                except PlaywrightTimeoutError:
                    raise ScraperError(f"Timeout fetching {domain}", "timeout", retryable=True)
                except Exception as e:
                    if isinstance(e, ScraperError):
                        raise e
                    raise ScraperError(f"Error fetching {domain}: {str(e)}", "fetch_error", retryable=True)
                
                # Human-like jitter
                await asyncio.sleep(random.uniform(1.5, 3.0))

                # Specific handling for X.com / Twitter
                if "x.com" in url or "twitter.com" in url:
                    try:
                        # Increased to 30s to handle X.com rate-limiting/slowness
                        await page.wait_for_selector('[data-testid="tweetText"]', timeout=30000)
                        await page.evaluate("window.scrollBy(0, 500)")
                        await asyncio.sleep(2) 
                    except Exception:
                        logger.warning(f"Tweet selector timeout for {domain}")

                # Get rendered content
                content = await page.content()

                # Save storage state (cookies/localStorage) for persistence
                await context.storage_state(path=storage_path)
                
            finally:
                await context.close()

            if content:
                return self._parse_content(content)
            return ""

    def _parse_content(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Metadata extraction
        metadata = {
            "title": "",
            "author": "",
            "publish_date": "",
            "images": []
        }
        
        # Title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text().strip()
        
        # Author (Common patterns)
        author_meta = soup.find("meta", attrs={"name": "author"}) or \
                     soup.find("meta", attrs={"property": "article:author"})
        if author_meta:
            metadata["author"] = author_meta.get("content", "").strip()
            
        # Publish Date
        date_meta = soup.find("meta", attrs={"name": "publish-date"}) or \
                   soup.find("meta", attrs={"property": "article:published_time"}) or \
                   soup.find("meta", attrs={"name": "date"})
        if date_meta:
            metadata["publish_date"] = date_meta.get("content", "").strip()

        # Images (All <img> tags with absolute URLs)
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.startswith("http"):
                metadata["images"].append(src)

        # Clean soup for text extraction
        for element in soup(["script", "style", "meta", "noscript", "svg"]):
            element.decompose()

        # Convert to markdown
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False
        converter.body_width = 0 
        
        markdown = converter.handle(str(soup))
        
        # Return structured data
        return {
            "metadata": metadata,
            "markdown": markdown
        }

    def get_active_contexts_count(self):
        return settings.MAX_CONCURRENT_BROWSERS - self.semaphore._value

# Standalone CLI
if __name__ == "__main__":
    import argparse

    async def main():
        parser = argparse.ArgumentParser(description="GhostFetch Stealth Scraper")
        parser.add_argument("url", help="URL to fetch")
        args = parser.parse_args()

        scraper = StealthScraper()
        try:
            result = await scraper.fetch(args.url)
            if result:
                logger.info("Successfully fetched and parsed content.")
                print("\n--- Metadata ---\n")
                import json
                print(json.dumps(result["metadata"], indent=2))
                print("\n--- Markdown ---\n")
                print(result["markdown"])
            else:
                logger.error("No content fetched.")
        except Exception as e:
            logger.critical(f"Fatal Error: {type(e).__name__} - {e}")
            sys.exit(1)
        finally:
            await scraper.stop()

    asyncio.run(main())
