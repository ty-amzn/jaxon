# Deployment

## Services & Ports

| Service | Port | Description |
|---------|------|-------------|
| Jaxon | 51430 | Main assistant API, webhooks, messaging bots |
| Town Square | 51431 | Feed/microblog service with web UI at `/feed/ui` |
| Observatory | 51432 | LLM metrics server with dashboard at `/observe/ui` |

All three services are defined in the root `docker-compose.yml`. No ports are exposed to the host — services communicate over a shared Docker network. Use a reverse proxy (Nginx Proxy Manager, Cloudflare tunnel, etc.) for browser access.

## Docker Compose (Recommended)

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f jaxon

# Rebuild after code changes
docker compose up -d --build

# Stop
docker compose down
```

Each service:
- Mounts its own `data/` directory for persistent storage
- Restarts automatically unless explicitly stopped
- Includes a health check (polled every 30 seconds)

---

## Docker with Ollama

To add a local LLM alongside the assistant, add an Ollama service:

```yaml
# Add to docker-compose.yml
  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    networks:
      - npm-shared

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

To add web search capabilities:

```yaml
# Add to docker-compose.yml
  searxng:
    image: searxng/searxng
    volumes:
      - ./searxng:/etc/searxng
    restart: unless-stopped
    networks:
      - npm-shared
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

## Reverse Proxy

Since no ports are exposed to the host, use a reverse proxy on the same Docker network to provide browser access. With Nginx Proxy Manager or similar, point proxy hosts at the container names:

| Domain | Upstream |
|--------|----------|
| `assistant.example.com` | `jaxon:51430` |
| `feed.example.com` | `townsquare:51431` |
| `observatory.example.com` | `observatory:51432` |

Or with plain nginx:

```nginx
server {
    listen 443 ssl;
    server_name assistant.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://jaxon:51430;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
