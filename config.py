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

settings = Settings()
