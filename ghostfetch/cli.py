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
from ghostfetch.version import __version__
from src.auth_session import auth_session_store
from src.utils.security import validate_domain_host


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



async def fetch_url(
    url: str,
    output_format: str = "markdown",
    auth_storage_state_path: Optional[str] = None,
) -> dict:
    """Fetch a URL and return the content."""
    # Import here to avoid slow startup for --help
    from src.core.scraper import StealthScraper
    
    scraper = StealthScraper()
    try:
        result = await scraper.fetch(url, auth_storage_state_path=auth_storage_state_path)
        return result
    finally:
        await scraper.stop()


def _resolve_cli_auth_storage(url: str, auth_session_id: Optional[str]) -> Optional[str]:
    if not auth_session_id:
        return None
    return auth_session_store.resolve_storage_path(auth_session_id, url)


def run_fetch(
    url: str,
    output_format: str = "markdown",
    metadata_only: bool = False,
    auth_session_id: Optional[str] = None,
):
    """Run the fetch command synchronously."""
    auth_storage_state_path = _resolve_cli_auth_storage(url, auth_session_id)
    result = asyncio.run(fetch_url(url, auth_storage_state_path=auth_storage_state_path))
    
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


async def _interactive_auth_login(domain: str, login_url: str, session_id: Optional[str], ttl_seconds: int):
    from playwright.async_api import async_playwright

    print(f"🔐 Opening browser for login at {login_url}")
    print("   Complete sign-in in the opened browser, then return here and press Enter.")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
        input("Press Enter after login is complete...")
        state = await context.storage_state()
        await browser.close()
    created = auth_session_store.create_session(
        domain=domain,
        storage_state=state,
        ttl_seconds=ttl_seconds,
        session_id=session_id,
    )
    print(json.dumps(created.to_dict(), indent=2))


def run_auth_login(domain: str, login_url: Optional[str], session_id: Optional[str], ttl_seconds: int):
    safe_domain = validate_domain_host(domain)
    if not login_url:
        login_url = f"https://{safe_domain}/login"
    asyncio.run(_interactive_auth_login(safe_domain, login_url, session_id, ttl_seconds))


def run_auth_status():
    print(json.dumps({"sessions": auth_session_store.list_sessions()}, indent=2))


def run_auth_revoke(session_id: str):
    removed = auth_session_store.revoke_session(session_id)
    if not removed:
        print("❌ Session not found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"status": "revoked", "session_id": session_id}, indent=2))


def main():
    """Main CLI entry point."""
    # Pre-process arguments to support ghostfetch <url> directly
    # If the first positional argument is not a known command, assume it's a URL
    # and insert the 'fetch' command implicitly.
    commands = ['serve', 'setup', 'fetch', 'auth']
    for i, arg in enumerate(sys.argv[1:], 1):
        if not arg.startswith('-'):
            if arg in commands:
                break
            # Not a known command, must be a URL or invalid choice
            # We insert 'fetch' to handle it gracefully
            sys.argv.insert(i, "fetch")
            break

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
    
    # Global flags (also available on subparsers for flexibility)
    parser.add_argument("--version", "-v", action="version", version=f"%(prog)s {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Shared flags for fetch operation
    fetch_shared = argparse.ArgumentParser(add_help=False)
    fetch_shared.add_argument("--json", action="store_true", help="Output as JSON")
    fetch_shared.add_argument("--metadata-only", action="store_true", help="Only output metadata")
    fetch_shared.add_argument("--quiet", "-q", action="store_true", help="Suppress progress messages")
    fetch_shared.add_argument("--auth-session-id", help="Authenticated session ID for login-gated pages")

    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch a URL (default command)", parents=[fetch_shared])
    fetch_parser.add_argument("url", help="URL to fetch")
    
    # Add shared flags to root too so they work before the command
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--metadata-only", action="store_true", help="Only output metadata")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress messages")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Install required browser dependencies")

    auth_parser = subparsers.add_parser("auth", help="Manage authenticated sessions")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command", help="Auth commands")
    auth_login = auth_subparsers.add_parser("login", help="Open browser login and save session state")
    auth_login.add_argument("--domain", required=True, help="Allowed domain for this session (e.g. linkedin.com)")
    auth_login.add_argument("--login-url", help="Full login URL to open in browser")
    auth_login.add_argument("--session-id", help="Optional session id")
    auth_login.add_argument("--ttl-seconds", type=int, default=86400, help="Session TTL in seconds (default: 86400)")

    auth_subparsers.add_parser("status", help="List auth sessions")
    auth_revoke = auth_subparsers.add_parser("revoke", help="Revoke an auth session")
    auth_revoke.add_argument("session_id", help="Session ID to revoke")
    
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
            
    elif args.command == "fetch":
        # Direct fetch mode
        url = args.url
        if not url:
            parser.print_help()
            sys.exit(0)
            
        if not args.quiet:
            print(f"🔍 Fetching {url}...", file=sys.stderr)
        
        # Auto-install browsers if needed (silent for non-interactive use)
        if not ensure_browsers_installed(quiet=args.quiet):
            if not args.quiet:
                print("❌ Browsers not installed. Run: ghostfetch setup", file=sys.stderr)
            sys.exit(1)
        
        output_format = "json" if args.json else "markdown"
        run_fetch(
            url,
            output_format=output_format,
            metadata_only=args.metadata_only,
            auth_session_id=args.auth_session_id,
        )

    elif args.command == "auth":
        if args.auth_command == "login":
            if not ensure_browsers_installed(quiet=False):
                print("❌ Browsers not installed. Run: ghostfetch setup", file=sys.stderr)
                sys.exit(1)
            run_auth_login(
                domain=args.domain,
                login_url=args.login_url,
                session_id=args.session_id,
                ttl_seconds=args.ttl_seconds,
            )
        elif args.auth_command == "status":
            run_auth_status()
        elif args.auth_command == "revoke":
            run_auth_revoke(args.session_id)
        else:
            auth_parser.print_help()
            sys.exit(1)
        
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
