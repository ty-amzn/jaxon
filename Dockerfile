FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
 && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy source
COPY src/ src/
COPY data/memory/IDENTITY.md data/memory/IDENTITY.md
COPY data/memory/MEMORY.md data/memory/MEMORY.md

# Install project
RUN uv sync --frozen --no-dev

# Install Playwright Chromium and its system dependencies
RUN uv run playwright install --with-deps chromium

# Create data directories
RUN mkdir -p data/memory/daily data/logs data/db data/skills data/automations

EXPOSE 51430

CMD ["uv", "run", "assistant", "serve", "--host", "0.0.0.0"]
