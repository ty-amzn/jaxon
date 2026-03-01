# Deployment

## Docker Compose (Recommended)

The included `docker-compose.yml` provides a production-ready setup:

```yaml
services:
  assistant:
    build: .
    ports:
      - "51430:51430"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:51430/health').raise_for_status()"]
      interval: 30s
      timeout: 5s
      retries: 3
```

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f assistant

# Rebuild after code changes
docker compose up -d --build

# Stop
docker compose down
```

The container:
- Exposes port 51430 for the API, webhooks, and Telegram webhook mode
- Mounts `./data` for persistent storage (memory, threads, databases, logs)
- Restarts automatically unless explicitly stopped
- Includes a health check that polls `/health` every 30 seconds

---

## Docker with Ollama

To run with a local LLM alongside the assistant:

```yaml
# docker-compose.yml
services:
  assistant:
    build: .
    ports:
      - "51430:51430"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    depends_on:
      - ollama
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:51430/health').raise_for_status()"]
      interval: 30s
      timeout: 5s
      retries: 3

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

```bash
# .env
ASSISTANT_OLLAMA_ENABLED=true
ASSISTANT_OLLAMA_BASE_URL=http://ollama:11434
ASSISTANT_OLLAMA_MODEL=llama3.2

# Pull the model after starting
docker compose exec ollama ollama pull llama3.2
```

---

## Docker with SearXNG

Add web search capabilities:

```yaml
services:
  # ... assistant and ollama services above ...

  searxng:
    image: searxng/searxng
    ports:
      - "8888:8080"
    volumes:
      - ./searxng:/etc/searxng
    restart: unless-stopped
```

```bash
# .env
ASSISTANT_WEB_SEARCH_ENABLED=true
ASSISTANT_SEARXNG_URL=http://searxng:8080
```

---

## Manual Deployment

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/ty-amzn/ai-assistant.git
cd ai-assistant
uv sync --all-extras

# Configure
cp .env.example .env
# Edit .env with your settings

# Run the API server (required for Telegram, scheduler, webhooks)
uv run assistant serve --host 0.0.0.0

# Or run the interactive CLI
uv run assistant chat
```

---

## Reverse Proxy (nginx)

For production deployments behind a reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name assistant.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:51430;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
