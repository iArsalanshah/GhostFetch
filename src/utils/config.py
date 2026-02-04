import os

class Settings:
    # API Settings
    HOST = os.getenv("GHOSTFETCH_HOST", "0.0.0.0")
    PORT = int(os.getenv("GHOSTFETCH_PORT", 8000))
    
    # Scraper Settings
    MAX_CONCURRENT_BROWSERS = int(os.getenv("MAX_CONCURRENT_BROWSERS", 2))
    MIN_DOMAIN_DELAY = int(os.getenv("MIN_DOMAIN_DELAY", 10))
    MAX_REQUESTS_PER_BROWSER = int(os.getenv("MAX_REQUESTS_PER_BROWSER", 50))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    
    # GitHub Settings
    GITHUB_REPO = os.getenv("GITHUB_REPO", "iArsalanshah/GhostFetch")
    
    # Persistence
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./storage/jobs.db")
    STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")
    
    # Job Policy
    JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", 86400))  # 24 hours

    # Sync Endpoint Settings
    SYNC_TIMEOUT_DEFAULT = float(os.getenv("SYNC_TIMEOUT_DEFAULT", 120.0))  # Default timeout for /fetch/sync
    MAX_SYNC_TIMEOUT = float(os.getenv("MAX_SYNC_TIMEOUT", 300.0))  # Maximum allowed timeout (5 minutes)

    # Proxy Settings
    PROXIES_FILE = os.getenv("PROXIES_FILE", "proxies.txt")
    PROXY_STRATEGY = os.getenv("PROXY_STRATEGY", "round_robin") # round_robin or random

    def get_proxies(self):
        if not os.path.exists(self.PROXIES_FILE):
            return []
        with open(self.PROXIES_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]

settings = Settings()
