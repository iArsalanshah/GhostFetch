# GhostFetch Docker Image
# Multi-stage build for smaller final image
# Supports: linux/amd64, linux/arm64

# Stage 1: Base with dependencies
FROM python:3.11-slim as base

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Builder
FROM base as builder

WORKDIR /app

# Install Python dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e .

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Stage 3: Final image
FROM base as final

# Create non-root user for security
RUN groupadd -r ghostfetch && useradd -r -g ghostfetch ghostfetch

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/ms-playwright /home/ghostfetch/.cache/ms-playwright

# Copy application code
COPY --chown=ghostfetch:ghostfetch . .

# Create storage directory with correct permissions
RUN mkdir -p /app/storage && chown -R ghostfetch:ghostfetch /app/storage

# Environment variables with sensible defaults
ENV GHOSTFETCH_HOST=0.0.0.0 \
    GHOSTFETCH_PORT=8000 \
    MAX_CONCURRENT_BROWSERS=2 \
    MIN_DOMAIN_DELAY=10 \
    SYNC_TIMEOUT_DEFAULT=120 \
    MAX_SYNC_TIMEOUT=300 \
    STORAGE_DIR=/app/storage \
    PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Switch to non-root user
USER ghostfetch

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Labels for Docker Hub
LABEL org.opencontainers.image.title="GhostFetch" \
      org.opencontainers.image.description="Stealthy headless browser service for AI agents. Bypasses anti-bot protections." \
      org.opencontainers.image.url="https://github.com/iArsalanshah/GhostFetch" \
      org.opencontainers.image.source="https://github.com/iArsalanshah/GhostFetch" \
      org.opencontainers.image.vendor="iArsalanshah" \
      org.opencontainers.image.licenses="MIT"
