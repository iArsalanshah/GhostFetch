#!/usr/bin/env python3
"""
GhostFetch CLI - Zero-setup command-line interface for AI agents.

Usage:
    ghostfetch <url>                    # Fetch content synchronously
    ghostfetch <url> --json             # Output as JSON
    ghostfetch <url> --metadata-only    # Only output metadata
    ghostfetch serve                    # Start the API server
    ghostfetch setup                    # Auto-install browser dependencies
"""

import argparse
import asyncio
import json
import subprocess
import sys
import os
from typing import Optional


def install_browsers(quiet: bool = False) -> bool:
    """Install Playwright browsers automatically."""
    try:
        if not quiet:
            print("📦 Installing Playwright browsers (this only happens once)...")
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=quiet,
            text=True
        )
        if result.returncode == 0:
            if not quiet:
                print("✅ Browser installation complete!")
            return True
        else:
            if not quiet:
                print(f"❌ Browser installation failed: {result.stderr}")
            return False
    except Exception as e:
        if not quiet:
            print(f"❌ Browser installation error: {e}")
        return False


def ensure_browsers_installed(quiet: bool = False) -> bool:
    """Ensure browsers are installed, installing if necessary."""
    # Try a quick browser launch to verify installation
    try:
        result = subprocess.run(
            [sys.executable, "-c", 
             "from playwright.sync_api import sync_playwright; "
             "p = sync_playwright().start(); "
             "b = p.chromium.launch(headless=True); "
             "b.close(); p.stop()"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True
    except subprocess.TimeoutExpired:
        if not quiet:
            print("⏳ Browser check timed out, attempting install...", file=sys.stderr)
    except Exception:
        pass
    
    # Browsers not ready, install them
    return install_browsers(quiet)



async def fetch_url(url: str, output_format: str = "markdown") -> dict:
    """Fetch a URL and return the content."""
    # Import here to avoid slow startup for --help
    from src.core.scraper import StealthScraper
    
    scraper = StealthScraper()
    try:
        result = await scraper.fetch(url)
        return result
    finally:
        await scraper.stop()


def run_fetch(url: str, output_format: str = "markdown", metadata_only: bool = False):
    """Run the fetch command synchronously."""
    result = asyncio.run(fetch_url(url))
    
    if not result:
        print("❌ No content fetched.", file=sys.stderr)
        sys.exit(1)
    
    if output_format == "json":
        if metadata_only:
            print(json.dumps(result["metadata"], indent=2))
        else:
            print(json.dumps(result, indent=2))
    else:
        if metadata_only:
            print("--- Metadata ---\n")
            print(json.dumps(result["metadata"], indent=2))
        else:
            print("--- Metadata ---\n")
            print(json.dumps(result["metadata"], indent=2))
            print("\n--- Markdown ---\n")
            print(result["markdown"])


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Start the GhostFetch API server."""
    import uvicorn
    print(f"🚀 Starting GhostFetch API server at http://{host}:{port}")
    print("   Endpoints:")
    print("     POST /fetch       - Submit async job")
    print("     POST /fetch/sync  - Synchronous fetch (blocks until complete)")
    print("     GET  /job/{id}    - Get job status")
    print("     GET  /health      - Health check")
    print("     GET  /metrics     - Prometheus metrics")
    print("")
    uvicorn.run("main:app", host=host, port=port, reload=reload)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ghostfetch",
        description="🔍 GhostFetch - Stealthy web fetcher for AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ghostfetch https://x.com/user/status/123     # Fetch a tweet
  ghostfetch https://example.com --json        # Output as JSON  
  ghostfetch https://example.com --metadata-only
  ghostfetch serve                             # Start API server
  ghostfetch serve --port 9000                 # Custom port
  ghostfetch setup                             # Install browsers
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Install required browser dependencies")
    
    # URL argument (for direct fetch)
    parser.add_argument("url", nargs="?", help="URL to fetch")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--metadata-only", action="store_true", help="Only output metadata")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress messages")
    parser.add_argument("--version", "-v", action="version", version="%(prog)s 2026.2.6")
    
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "serve":
        # Ensure browsers before serving
        if not ensure_browsers_installed(quiet=False):
            print("❌ Failed to install browsers. Please run: ghostfetch setup", file=sys.stderr)
            sys.exit(1)
        run_server(host=args.host, port=args.port, reload=args.reload)
        
    elif args.command == "setup":
        print("🔧 GhostFetch Setup")
        print("==================")
        if install_browsers(quiet=False):
            print("\n✅ Setup complete! You can now use ghostfetch.")
        else:
            print("\n❌ Setup failed. Please try manually: playwright install chromium")
            sys.exit(1)
            
    elif args.url:
        # Direct fetch mode
        if not args.quiet:
            print(f"🔍 Fetching {args.url}...", file=sys.stderr)
        
        # Auto-install browsers if needed (silent for non-interactive use)
        if not ensure_browsers_installed(quiet=args.quiet):
            if not args.quiet:
                print("❌ Browsers not installed. Run: ghostfetch setup", file=sys.stderr)
            sys.exit(1)
        
        output_format = "json" if args.json else "markdown"
        run_fetch(args.url, output_format=output_format, metadata_only=args.metadata_only)
        
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
