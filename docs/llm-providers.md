# LLM Providers

The assistant supports multiple LLM providers. Configure your preferred default:

```bash
ASSISTANT_DEFAULT_PROVIDER=claude   # claude | openai | gemini | ollama | bedrock
```

---

## Claude (Anthropic)

The default provider. Requires an API key:

```bash
ANTHROPIC_API_KEY=sk-ant-...
ASSISTANT_MODEL=claude-sonnet-4-20250514
```

---

## OpenAI

```bash
OPENAI_API_KEY=sk-...
ASSISTANT_OPENAI_ENABLED=true
ASSISTANT_OPENAI_MODEL=gpt-4o
```

---

## Google Gemini

```bash
GEMINI_API_KEY=your-key
ASSISTANT_GEMINI_ENABLED=true
ASSISTANT_GEMINI_MODEL=gemini-2.0-flash
```

---

## AWS Bedrock

Uses the native Converse API with boto3. Auth via standard AWS credential chain (AWS_PROFILE, IAM roles, env vars) — no API key needed.

```bash
ASSISTANT_BEDROCK_ENABLED=true
ASSISTANT_BEDROCK_REGION=us-east-1
ASSISTANT_BEDROCK_MODEL=us.anthropic.claude-sonnet-4-20250514-v1:0
```

Configure AWS credentials the usual way:
- `AWS_PROFILE` environment variable
- `~/.aws/credentials` file
- IAM instance roles (EC2/ECS/Lambda)

---

## Ollama (Local LLMs)

Run queries through local models for privacy and cost savings.

### Setup

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull llama3.2`
3. Start Ollama: `ollama serve`

### Configuration

```bash
ASSISTANT_OLLAMA_ENABLED=true
ASSISTANT_OLLAMA_BASE_URL=http://localhost:11434
ASSISTANT_OLLAMA_MODEL=llama3.2
```

### Routing Threshold

Adjust `ASSISTANT_LOCAL_MODEL_THRESHOLD_TOKENS` to control when Ollama is used (lower = more Ollama, higher = more cloud provider).

---

## Smart Routing

When Ollama is enabled alongside a cloud provider, the router automatically selects the best provider:

| Condition | Provider |
|-----------|----------|
| Tool use required | Default cloud provider |
| Long/complex messages (>threshold tokens) | Default cloud provider |
| Provider unavailable | Fallback to next available |
| Simple queries | Ollama (if enabled) |

---

## Web Search

Search the web using a self-hosted SearXNG instance.

### Setup

1. Deploy SearXNG: https://github.com/searxng/searxng
2. Enable the JSON API in SearXNG settings

### Configuration

```bash
ASSISTANT_WEB_SEARCH_ENABLED=true
ASSISTANT_SEARXNG_URL=http://localhost:8888
```

### Usage

Once enabled, the assistant automatically uses web search when relevant:

```
You: What's the latest news about Rust?
```

The `web_search` tool accepts a `query` parameter and optional `num_results` (default 5, max 10).

---

## Vector Search

Semantic similarity search over conversation history using embeddings.

### Setup

Requires Ollama with an embedding model:

```bash
ollama pull nomic-embed-text
```

### Configuration

```bash
ASSISTANT_VECTOR_SEARCH_ENABLED=true
ASSISTANT_EMBEDDING_MODEL=nomic-embed-text
```

### How It Works

Every message is embedded and stored in `data/db/embeddings.db`. When you ask about past topics, the system finds semantically related conversations — not just keyword matches.
