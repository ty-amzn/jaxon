FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for caching
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project 2>/dev/null || uv sync --no-dev --no-install-project

# Copy source
COPY src/ src/

# Install project
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN mkdir -p data

EXPOSE 51431

CMD ["uv", "run", "townsquare", "serve", "--host", "0.0.0.0"]
