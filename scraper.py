import asyncio
import random
import sys
import time
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
import html2text

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

    async def start(self):
        self.playwright = await async_playwright().start()
        # Launch options for stealth
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
        if self.playwright:
            await self.playwright.stop()

    async def fetch(self, url: str):
        if not self.browser:
            await self.start()

        context = await self.browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            java_script_enabled=True,
        )

        # Basic stealth - removing 'webdriver' and mocking basics
        # Removed the amateur canvas poisoning as it is a major detection signal
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)

        page = await context.new_page()
        content = ""
        try:
            # Simple logging - path/query secrets exist, so we just log the action
            print(f"Requesting URL...")
            
            # Reverted to 60s timeout to handle slow loads/rate limits
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Add a random human-like jitter
            await asyncio.sleep(random.uniform(1.5, 3.0))

            # Specific handling for X.com / Twitter
            if "x.com" in url or "twitter.com" in url:
                # Wait for content to actually load
                try:
                    await page.wait_for_selector('[data-testid="tweetText"]', timeout=30000)
                    # Scroll to trigger lazy loading
                    await page.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(2) 
                except Exception as e:
                    print(f"Selector Warning: {type(e).__name__}", file=sys.stderr)

            # Get final rendered content
            content = await page.content()
            
        except Exception as e:
            # Proper error reporting - no more silent swallowing
            print(f"Critical Fetch Error: {type(e).__name__} - {str(e)}", file=sys.stderr)
            raise e
        finally:
            await context.close()

        if content:
            return self._parse_content(content)
        return ""

    def _parse_content(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove scripts, styles, metadata
        for element in soup(["script", "style", "meta", "noscript", "svg"]):
            element.decompose()

        # Convert to markdown
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False
        converter.body_width = 0 
        
        markdown = converter.handle(str(soup))
        
        # Removed the broken regex scrubbing and "Sandbox" ASCII art
        # Security Note: User must treat this output as untrusted data.
        return markdown

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
                print("\n--- Result ---\n")
                print(result)
            else:
                print("No content fetched.", file=sys.stderr)
        except Exception as e:
            print(f"Fatal: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            await scraper.stop()

    asyncio.run(main())
