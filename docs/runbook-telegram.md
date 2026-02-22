# Runbook: Telegram Bot Integration

## Overview

The Telegram bot uses **python-telegram-bot v21** (async). It supports two
transport modes:

| Mode | When to use |
|------|-------------|
| **Long-polling** (default) | Local dev, simple deployments — no public URL needed |
| **Webhook** | Production / Docker — lower latency, no persistent connection |

Each Telegram user gets their own isolated assistant session keyed by `chat_id`.
Tool permission requests surface as inline Approve / Deny buttons in the chat.

---

## Step 1 — Create a bot and get a token

1. Open Telegram and start a conversation with **@BotFather**.
2. Send `/newbot` and follow the prompts (name → username ending in `bot`).
3. Copy the token — it looks like `110201543:AAHdqTcvCH1vGWJxfSeofSs4tQ6CStAbE`.

---

## Step 2 — Find your Telegram user ID

You need your numeric user ID to whitelist yourself.

1. Start a conversation with **@userinfobot** (or **@getidsbot**).
2. It will reply with your user ID, e.g. `123456789`.

---

## Step 3 — Configure `.env`

```dotenv
ASSISTANT_TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=110201543:AAHdqTcvCH1vGWJxfSeofSs4tQ6CStAbE

# Comma-separated numeric IDs of users who may interact with the bot.
# Leave blank to allow anyone who finds the bot (not recommended).
ASSISTANT_TELEGRAM_ALLOWED_USER_IDS=123456789

# Leave blank for long-polling (default). Set to your public HTTPS URL for webhook.
ASSISTANT_TELEGRAM_WEBHOOK_URL=
```

---

## Step 4 — Run (long-polling)

```bash
uv run assistant serve
```

The server starts the bot in polling mode automatically when
`ASSISTANT_TELEGRAM_ENABLED=true` and no webhook URL is set. You will see:

```
INFO  Starting Telegram bot in polling mode
```

Open Telegram, send `/start` to your bot, then chat normally.

---

## Step 4 (alt) — Run with webhook

Webhooks require a public HTTPS URL that Telegram can reach.

### Option A: ngrok (local dev)

```bash
ngrok http 8000
# Note the https URL, e.g. https://abc123.ngrok-free.app
```

Set in `.env`:

```dotenv
ASSISTANT_TELEGRAM_WEBHOOK_URL=https://abc123.ngrok-free.app/telegram/webhook
```

### Option B: Production (reverse proxy)

Point your HTTPS domain to the assistant on port 8000, then set:

```dotenv
ASSISTANT_TELEGRAM_WEBHOOK_URL=https://assistant.example.com/telegram/webhook
```

> **Note:** Telegram requires the webhook URL to use **HTTPS on port 443, 80, 88,
> or 8443**. Self-signed certificates are supported only with an explicit
> certificate upload — use a proper CA cert in production.

---

## Available bot commands

| Command | Description |
|---------|-------------|
| `/start` | Verify the bot is reachable and you are authorized |
| `/status` | Show current session ID, message count, and model in use |
| `/schedule` | List active scheduled jobs (requires scheduler enabled) |
| `/watch` | List paths being watched by watchdog (requires watchdog enabled) |
| Any text | Sent to the assistant; reply is streamed back as a message |

---

## Tool permission flow

When the assistant wants to run a tool (e.g. execute a shell command), it sends
an **inline keyboard** message:

```
Permission request [shell_exec]:
Run shell command: ls -la /tmp

  [Approve]  [Deny]
```

You have **30 seconds** to respond. Unanswered requests default to **denied**.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Bot does not respond | Confirm `TELEGRAM_BOT_TOKEN` is correct; check `data/logs/app.log` |
| "Not authorized." reply | Your user ID is not in `ASSISTANT_TELEGRAM_ALLOWED_USER_IDS` |
| Webhook returns 404 | Confirm the assistant server is running and the URL path is `/telegram/webhook` |
| Duplicate messages in webhook mode | You have both polling and a stale webhook set — call `https://api.telegram.org/bot<TOKEN>/deleteWebhook` to reset |
| Messages cut off | Long replies are chunked at 4000 chars automatically; check for errors in logs |

---

## Docker notes

When running inside Docker, the server is exposed on the host. For webhook mode,
pass the public URL via environment variable in `docker-compose.yml`:

```yaml
environment:
  - ASSISTANT_TELEGRAM_ENABLED=true
  - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  - ASSISTANT_TELEGRAM_ALLOWED_USER_IDS=${ASSISTANT_TELEGRAM_ALLOWED_USER_IDS}
  - ASSISTANT_TELEGRAM_WEBHOOK_URL=https://assistant.example.com/telegram/webhook
```
