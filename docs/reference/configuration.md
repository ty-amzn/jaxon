# Configuration Reference

All settings can be set in `.env`. Settings use the `ASSISTANT_` prefix unless noted.

---

## Core

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | `""` | Anthropic API key (no prefix) |
| `ASSISTANT_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `ASSISTANT_MAX_TOKENS` | `8192` | Max response tokens |
| `ASSISTANT_DATA_DIR` | `./data` | Data directory path |
| `ASSISTANT_HOST` | `127.0.0.1` | API server host |
| `ASSISTANT_PORT` | `51430` | API server port |
| `ASSISTANT_LOG_LEVEL` | `INFO` | Logging level |
| `ASSISTANT_MAX_CONTEXT_MESSAGES` | `50` | Max messages in context |
| `ASSISTANT_MAX_TOOL_ROUNDS` | `10` | Max tool calls per LLM response |
| `ASSISTANT_AUTO_APPROVE_READS` | `true` | Auto-approve read operations |
| `ASSISTANT_DEFAULT_PROVIDER` | `claude` | Default LLM provider |

## AWS Bedrock

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_BEDROCK_ENABLED` | `false` | Enable Bedrock provider |
| `ASSISTANT_BEDROCK_REGION` | `us-east-1` | AWS region |
| `ASSISTANT_BEDROCK_MODEL` | `us.anthropic.claude-sonnet-4-20250514-v1:0` | Bedrock model ID |

No API key settings — uses the standard AWS credential chain (AWS_PROFILE, ~/.aws/credentials, IAM roles).

## OpenAI

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | `""` | OpenAI API key (no prefix) |
| `ASSISTANT_OPENAI_ENABLED` | `false` | Enable OpenAI provider |
| `ASSISTANT_OPENAI_MODEL` | `gpt-4o` | OpenAI model |

## Google Gemini

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | `""` | Gemini API key (no prefix) |
| `ASSISTANT_GEMINI_ENABLED` | `false` | Enable Gemini provider |
| `ASSISTANT_GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model |

## Ollama

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_OLLAMA_ENABLED` | `false` | Enable local LLM |
| `ASSISTANT_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `ASSISTANT_OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `ASSISTANT_LOCAL_MODEL_THRESHOLD_TOKENS` | `1000` | Routing threshold |

## Search

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_WEB_SEARCH_ENABLED` | `false` | Enable web search |
| `ASSISTANT_SEARXNG_URL` | `http://localhost:8888` | SearXNG instance URL |
| `ASSISTANT_VECTOR_SEARCH_ENABLED` | `false` | Enable vector search |
| `ASSISTANT_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |

## Media

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_MAX_MEDIA_SIZE_MB` | `10` | Max image size |

## Google Maps

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_GOOGLE_MAPS_ENABLED` | `false` | Enable Google Maps tool |
| `GOOGLE_MAPS_API_KEY` | `""` | Google Maps API key (no prefix) |

## YouTube & Reddit

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_YOUTUBE_ENABLED` | `false` | Enable YouTube search/transcripts |
| `ASSISTANT_REDDIT_ENABLED` | `false` | Enable Reddit search/browsing |

## Telegram

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_TELEGRAM_ENABLED` | `false` | Enable Telegram bot |
| `TELEGRAM_BOT_TOKEN` | `""` | Bot token (no prefix) |
| `ASSISTANT_TELEGRAM_ALLOWED_USER_IDS` | `""` | Comma-separated Telegram user IDs |
| `ASSISTANT_TELEGRAM_WEBHOOK_URL` | `""` | Webhook URL for bot |

## WhatsApp

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_WHATSAPP_ENABLED` | `false` | Enable WhatsApp bot |
| `ASSISTANT_WHATSAPP_ALLOWED_NUMBERS` | `""` | Comma-separated E.164 numbers |
| `ASSISTANT_WHATSAPP_SESSION_NAME` | `assistant` | Session name |

## Slack

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_SLACK_ENABLED` | `false` | Enable Slack bot |
| `SLACK_BOT_TOKEN` | `""` | Bot token (no prefix) |
| `SLACK_APP_TOKEN` | `""` | App-level token for Socket Mode (no prefix) |
| `ASSISTANT_SLACK_ALLOWED_USER_IDS` | `""` | Comma-separated Slack user IDs |
| `ASSISTANT_SLACK_ALLOWED_CHANNEL_IDS` | `""` | Comma-separated channel IDs |

## Scheduler

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_SCHEDULER_ENABLED` | `false` | Enable scheduler |
| `ASSISTANT_SCHEDULER_TIMEZONE` | `UTC` | Scheduler timezone |

## File Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_WATCHDOG_ENABLED` | `false` | Enable file monitoring |
| `ASSISTANT_WATCHDOG_PATHS` | `""` | Comma-separated paths to watch |
| `ASSISTANT_WATCHDOG_DEBOUNCE_SECONDS` | `2.0` | Debounce interval |
| `ASSISTANT_WATCHDOG_ANALYZE` | `false` | Analyze changes with AI |

## Webhooks

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_WEBHOOK_ENABLED` | `false` | Enable webhooks |
| `ASSISTANT_WEBHOOK_SECRET` | `""` | Bearer token for webhook auth |

## Do Not Disturb

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_DND_ENABLED` | `false` | Enable DND |
| `ASSISTANT_DND_START` | `23:00` | DND start (HH:MM) |
| `ASSISTANT_DND_END` | `07:00` | DND end (HH:MM) |
| `ASSISTANT_DND_ALLOW_URGENT` | `true` | Allow urgent during DND |

## Town Square (Feed)

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_TOWNSQUARE_URL` | `""` | Town Square service URL (enables feed tools) |

## Plugins & Agents

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_PLUGINS_ENABLED` | `false` | Enable plugin system |
| `ASSISTANT_AGENTS_ENABLED` | `false` | Enable agent delegation |

---

## Troubleshooting

### Ollama Not Connecting

1. Check if running: `curl http://localhost:11434/api/tags`
2. Verify model is pulled: `ollama list`
3. Check `ASSISTANT_OLLAMA_BASE_URL`

### Web Search Not Working

1. Verify SearXNG: `curl http://localhost:8888/search?q=test&format=json`
2. Ensure JSON API is enabled in SearXNG settings
3. Check `ASSISTANT_WEB_SEARCH_ENABLED=true`

### Vector Search Errors

1. Ollama must be running (embeddings use Ollama)
2. Pull the model: `ollama pull nomic-embed-text`
3. Ensure `data/db/` is writable

### Images Not Loading

1. Use absolute file paths
2. Verify format is supported (PNG, JPEG, GIF, WebP)
3. Check file is under the size limit

### Threads Not Saving

1. Check `data/threads/` exists and is writable

### Scheduler Not Running

1. Verify `ASSISTANT_SCHEDULER_ENABLED=true`
2. The scheduler requires the API server: `uv run assistant serve`

### Webhooks Not Responding

1. Verify `ASSISTANT_WEBHOOK_ENABLED=true`
2. The API server must be running
3. Check that the workflow name in the URL matches a loaded workflow

### Telegram Bot Not Responding

1. Check `ASSISTANT_TELEGRAM_ENABLED=true` and `TELEGRAM_BOT_TOKEN` is set
2. Verify your user ID is in `ASSISTANT_TELEGRAM_ALLOWED_USER_IDS`
3. The bot requires the API server: `uv run assistant serve`

### WhatsApp Bot Not Responding

1. Check `ASSISTANT_WHATSAPP_ENABLED=true`
2. Verify allowed numbers are in E.164 format
3. Re-scan QR code if session expired

### Permission Prompt Not Visible

If the `Approve? [y/N]` prompt doesn't appear during tool calls, this may be a Rich Live rendering issue. The prompt should pause the streaming display — if it doesn't, check that you're running the latest version.
