# Runbook: WhatsApp Bot Integration

## Overview

The WhatsApp bot uses **neonize** (a Go-backed Python library built on
whatsmeow) with the **linked-device** protocol. This means:

- No business API, no Meta approval — it links like WhatsApp Web.
- First-run requires scanning a QR code in your terminal to pair.
- Auth state is persisted in an SQLite file so subsequent restarts reconnect
  automatically without re-scanning.
- Each sender's phone number gets its own isolated assistant session.

> **Important:** This uses the unofficial WhatsApp linked-device protocol.
> Use it for personal automation only. Meta's ToS prohibit bulk messaging or
> commercial use via this method.

---

## Prerequisites

neonize depends on a compiled Go binary that it downloads automatically on
first import. You need:

- Python 3.11+
- Internet access on first run (to fetch the neonize Go binary)
- A WhatsApp account on a **secondary phone/SIM** (recommended) — the account
  will be tied up as a linked device while the bot runs.

The dependency is already in `pyproject.toml`:

```toml
neonize>=0.3.0
```

If you have not already synced:

```bash
uv sync --all-extras
```

---

## Step 1 — Configure `.env`

```dotenv
ASSISTANT_WHATSAPP_ENABLED=true

# Comma-separated E.164 numbers allowed to chat with the bot.
# Leave blank to allow any number that messages it (not recommended).
ASSISTANT_WHATSAPP_ALLOWED_NUMBERS=+15551234567,+442071234567

# Name of the session (used as the SQLite filename in data/whatsapp_auth/).
# Change this if you want to run multiple bots from the same data directory.
ASSISTANT_WHATSAPP_SESSION_NAME=assistant
```

---

## Step 2 — First-run pairing (QR code)

Start the server:

```bash
uv run assistant serve
```

On first run you will see a QR code printed to the terminal (or logs):

```
INFO  Starting WhatsApp bot (scan QR code to link device)
█████████████████████████
█ ▄▄▄▄▄ █▀█ █▄ ▄ █ ▄▄▄▄▄ █
...
```

On your phone:

1. Open WhatsApp → **Settings → Linked Devices → Link a Device**.
2. Point the camera at the QR code in the terminal.
3. The device links within a few seconds and you will see:

```
INFO  WhatsApp bot connected
```

Auth state is saved to `data/whatsapp_auth/assistant.sqlite3`. Subsequent
restarts reconnect without a QR code.

---

## Step 3 — Test it

From any allowed phone number, send a WhatsApp message to the number that is
running the bot. You should receive a reply.

To test from the same device as the bot account, message it from a different
account or use WhatsApp Web.

---

## Session management

| File | Purpose |
|------|---------|
| `data/whatsapp_auth/<session_name>.sqlite3` | neonize auth state — keys, registration |

**To unlink the bot** (e.g. to pair a different account):

1. On your phone: **Settings → Linked Devices** → select the device → **Log Out**.
2. Delete `data/whatsapp_auth/<session_name>.sqlite3`.
3. Restart the server — a new QR code will appear.

**To rename a session** without re-pairing, rename the SQLite file and update
`ASSISTANT_WHATSAPP_SESSION_NAME` to match.

---

## Allowlist behaviour

| `ASSISTANT_WHATSAPP_ALLOWED_NUMBERS` | Effect |
|--------------------------------------|--------|
| Empty | Any number that messages the bot gets a response |
| One or more E.164 numbers | Only listed numbers get responses; others are silently ignored and logged as warnings |

Numbers are matched with or without the leading `+`, so `+15551234567` and
`15551234567` are treated the same.

---

## Message handling details

- **Text messages and quoted replies** are handled; media (images, audio, etc.)
  is currently ignored.
- Replies from the bot are chunked at **4000 characters** per message to stay
  within WhatsApp limits.
- Messages sent *by the bot itself* are ignored (no echo loop).
- Each sender gets a separate session keyed as `whatsapp_<digits>`, so
  conversation history is per-contact.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| QR code never appears | neonize failed to download its Go binary — check internet access and rerun |
| QR code appears but linking fails | Ensure the phone has a stable internet connection during the scan |
| Bot was connected but stops responding after phone restart | This is normal — reconnect by restarting the server; neonize will re-register from the SQLite file |
| "Unauthorized" warning in logs | The sender's number is not in `ASSISTANT_WHATSAPP_ALLOWED_NUMBERS` |
| Bot connected but no reply | Check `data/logs/app.log` for exceptions in `handle_message` |
| `neonize` import error on install | Ensure you are on Python 3.11+ and `uv sync` completed without errors |

---

## Docker notes

The auth SQLite file must persist across container restarts. Mount the
`data/whatsapp_auth` directory as a volume:

```yaml
# docker-compose.yml
volumes:
  - ./data/whatsapp_auth:/app/data/whatsapp_auth
```

For first-run QR code pairing inside Docker, attach to the container's stdout:

```bash
docker compose up   # (not -d) — watch for the QR code in the terminal output
```

After pairing, you can restart in detached mode:

```bash
docker compose up -d
```

---

## Security considerations

- Keep `ASSISTANT_WHATSAPP_ALLOWED_NUMBERS` populated in any deployment exposed
  beyond your local machine.
- The SQLite auth file contains your WhatsApp session keys — treat it like a
  password and do not commit it to version control. It is already in
  `.gitignore` via `data/`.
- Tool permission gates apply normally; the bot will ask for approval (logged
  to `data/logs/audit.jsonl`) before executing destructive tools.
