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
from src.utils.config import settings
from src.core.stealth_utils import ProxyManager, FingerprintGenerator, RoundRobinStrategy, RandomStrategy

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

class StealthScraper:
    def __init__(self):
        self.browser = None
        self.playwright = None
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_BROWSERS)
        self.restart_lock = asyncio.Lock()
        self.last_fetch = {} # {domain: timestamp}
        self.domain_fingerprints = {}  # {domain: (fingerprint, timestamp)}
        self.fingerprint_ttl = 3600  # 1 hour coherence
        self.requests_count = 0
        
        # Initialize Proxy Manager
        proxies = settings.get_proxies()
        strategy = RandomStrategy() if settings.PROXY_STRATEGY == "random" else RoundRobinStrategy()
        self.proxy_manager = ProxyManager(proxies, strategy)
        if proxies:
            logger.info(f"Loaded {len(proxies)} proxies with {settings.PROXY_STRATEGY} strategy.")

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
            
            # Session Coherence: Cache fingerprint per domain
            if domain in self.domain_fingerprints:
                fp, ts = self.domain_fingerprints[domain]
                if time.time() - ts < self.fingerprint_ttl:
                    fingerprint = fp
                else:
                    fingerprint = FingerprintGenerator.generate()
                    self.domain_fingerprints[domain] = (fingerprint, time.time())
            else:
                fingerprint = FingerprintGenerator.generate()
                self.domain_fingerprints[domain] = (fingerprint, time.time())
            
            context_kwargs = {
                "user_agent": fingerprint["user_agent"],
                "viewport": fingerprint["viewport"],
                "locale": fingerprint["locale"],
                "timezone_id": fingerprint["timezone_id"],
                "java_script_enabled": True,
            }

            # Apply Proxy Rotation
            proxy_url = self.proxy_manager.get_next_proxy()
            if proxy_url:
                logger.info(f"Using proxy: {proxy_url}")
                context_kwargs["proxy"] = {"server": proxy_url}

            if os.path.exists(storage_path):
                logger.debug(f"Loading session for {domain}...")
                context_kwargs["storage_state"] = storage_path

            context = await self.browser.new_context(**context_kwargs)

            # Advanced Stealth Fingerprinting
            await context.add_init_script(FingerprintGenerator.get_stealth_script(fingerprint))

            page = await context.new_page()
            content = ""
            start_time = time.time()
            try:
                # Secure domain-only logging
                logger.info(f"Fetching {domain}...")
                
                # 60s timeout for page load
                try:
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    if not response:
                        if proxy_url: self.proxy_manager.mark_bad(proxy_url)
                        raise ScraperError(f"No response from {domain}", "no_response", retryable=True)
                    
                    if response.status >= 400:
                        if proxy_url: self.proxy_manager.mark_bad(proxy_url)
                        retryable = response.status in [408, 429, 500, 502, 503, 504]
                        raise ScraperError(f"HTTP {response.status} from {domain}", f"http_{response.status}", retryable=retryable)

                    # Performance: Record latency and mark proxy as good
                    latency_ms = (time.time() - start_time) * 1000
                    if proxy_url:
                        self.proxy_manager.record_latency(proxy_url, latency_ms)
                        self.proxy_manager.mark_good(proxy_url)

                except PlaywrightTimeoutError:
                    if proxy_url: self.proxy_manager.mark_bad(proxy_url)
                    raise ScraperError(f"Timeout fetching {domain}", "timeout", retryable=True)
                except Exception as e:
                    if proxy_url: self.proxy_manager.mark_bad(proxy_url)
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
