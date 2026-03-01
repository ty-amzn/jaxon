# Slack Bot

Chat with the assistant from Slack using Socket Mode (WebSocket connection, no public URL needed). Supports tool approval via Block Kit interactive buttons.

---

## Setup

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps)
2. Enable **Socket Mode** and generate an App-Level Token (`xapp-...`)
3. Add Bot Token Scopes: `chat:write`, `app_mentions:read`, `im:history`, `im:read`, `im:write`
4. Subscribe to bot events: `message.im` (direct messages)
5. Install the app to your workspace and copy the Bot Token (`xoxb-...`)

---

## Configuration

```bash
ASSISTANT_SLACK_ENABLED=true
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
ASSISTANT_SLACK_ALLOWED_USER_IDS=U01ABC123,U02DEF456
ASSISTANT_SLACK_ALLOWED_CHANNEL_IDS=
```

---

## Usage

DM the bot in Slack or invite it to a channel. When a tool requires approval, the bot sends a Block Kit message with **Approve** / **Deny** buttons. Background task results are delivered to the channel where the request originated.

---

## Access Control

- `ASSISTANT_SLACK_ALLOWED_USER_IDS` — comma-separated Slack user IDs (e.g. `U01ABC123`)
- `ASSISTANT_SLACK_ALLOWED_CHANNEL_IDS` — comma-separated channel IDs (e.g. `C01XYZ789`)
- If either list is empty, that dimension is unrestricted
