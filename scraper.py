import asyncio
import random
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

        # Enhance stealth by removing 'webdriver' property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = await context.new_page()
        content = ""
        try:
            print(f"Navigating to {url}...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Specific handling for X.com / Twitter to ensure tweets load
            if "x.com" in url or "twitter.com" in url:
                print("Detected X/Twitter, waiting for tweet text...")
                try:
                    # Wait for the main tweet text to appear
                    await page.wait_for_selector('[data-testid="tweetText"]', timeout=10000)
                    # Scroll a bit to trigger lazy loading if needed
                    await page.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(2) 
                except Exception as e:
                    print(f"Warning: Tweet selector wait timed out: {e}")

            # Get content
            content = await page.content()
            
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        finally:
            await context.close()

        # Parse and convert to Markdown
        if content:
            return self._parse_content(content)
        return "Failed to fetch content."

    def _parse_content(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove scripts, styles, metadata
        for element in soup(["script", "style", "meta", "noscript", "svg"]):
            element.decompose()

        # Convert to markdown
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False
        converter.body_width = 0  # No wrapping
        
        markdown = converter.handle(str(soup))
        return markdown

# Standalone CLI
if __name__ == "__main__":
    import argparse
    import sys

    async def main():
        parser = argparse.ArgumentParser(description="Stealth fetcher CLI")
        parser.add_argument("url", help="URL to fetch")
        args = parser.parse_args()

        scraper = StealthScraper()
        try:
            print(f"Fetching {args.url}...")
            result = await scraper.fetch(args.url)
            print("\n--- Result ---\n")
            print(result)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
        finally:
            await scraper.stop()

    asyncio.run(main())
