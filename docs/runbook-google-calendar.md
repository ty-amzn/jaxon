# Runbook: Google Calendar Integration

## Overview

The assistant can read and write events via the **Google Calendar API v3**.
When enabled, the existing `calendar` tool switches from the local SQLite
backend to Google Calendar — no tool schema changes needed.

| Feature | How it works |
|---------|--------------|
| **Read events** | Queries all calendars visible to the Google account (primary + shared) |
| **Create / update / delete** | Writes to the primary calendar |
| **Shared calendars** | Share other calendars *into* the Google account — they appear automatically |
| **macOS / iOS sync** | Add the Google account in System Settings → Internet Accounts; events show up in Apple Calendar |

Authentication uses OAuth2 with a Desktop app flow. A refresh token is saved
locally so the assistant can act on your behalf without re-prompting.

---

## Step 1 — Create a Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. "AI Assistant").
3. Navigate to **APIs & Services → Library**.
4. Search for **Google Calendar API** and click **Enable**.

---

## Step 2 — Create OAuth credentials

1. Go to **APIs & Services → Credentials**.
2. Click **Create Credentials → OAuth client ID**.
3. If prompted, configure the **OAuth consent screen** first:
   - User type: **External** (or Internal if using Google Workspace).
   - App name: anything (e.g. "AI Assistant").
   - Scopes: add `https://www.googleapis.com/auth/calendar`.
   - Test users: add the Gmail address the assistant will use.
4. Back on Credentials, select **Application type → Desktop app**.
5. Name it (e.g. "Assistant CLI") and click **Create**.
6. Copy the **Client ID** and **Client Secret**.

> **Tip:** While the app is in "Testing" status, only test users you
> explicitly add can complete the OAuth flow. This is fine for personal use —
> you never need to publish it.

---

## Step 3 — Configure `.env`

```dotenv
# Google Calendar
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...

# Enable after completing Step 4
ASSISTANT_GOOGLE_CALENDAR_ENABLED=true
```

---

## Step 4 — Authenticate

```bash
uv run assistant google-auth
```

This opens a browser for Google consent. Sign in with the Gmail account the
assistant should use, grant Calendar access, and the CLI saves the refresh
token to `data/google_auth/credentials.json`.

You only need to do this once. The token auto-refreshes on each use.

---

## Step 5 — Verify

```bash
uv run assistant chat
```

Try these prompts:

| Prompt | Expected |
|--------|----------|
| "What's on my calendar today?" | Lists events from all visible calendars |
| "Add a meeting tomorrow at 2pm called Team Sync" | Creates an event on the primary calendar |
| "Update that meeting to 3pm" | Patches the event |
| "Delete the Team Sync meeting" | Removes the event |

Check Apple Calendar — new events should appear within seconds (Google sync
push is near-instant to connected Apple devices).

---

## Shared calendars

The assistant reads from **all calendars** visible to the Google account, not
just the primary one. To give it visibility into other calendars:

1. From the other Google account, go to [Google Calendar settings](https://calendar.google.com/calendar/r/settings).
2. Click the calendar → **Share with specific people**.
3. Add the assistant's Gmail address.
4. Choose permission level:
   - **See all event details** — read-only.
   - **Make changes to events** — if the assistant should be able to modify events on that calendar.

Shared calendars appear automatically — no `add_feed` action needed. The
`.ics` feed actions (`add_feed`, `remove_feed`, `sync_feeds`) return a
message explaining this when Google mode is active.

---

## Permissions

When Google Calendar is enabled, tool permissions change because all
operations hit the network:

| Action | Permission | Approval needed? |
|--------|-----------|------------------|
| `list`, `today` | `NETWORK_READ` | No (auto-approved) |
| `create`, `update` | `NETWORK_WRITE` | Yes |
| `delete` | `NETWORK_WRITE` | Yes |
| `add_feed`, `remove_feed`, `sync_feeds` | `NETWORK_READ` | No (returns info message) |

In SQLite-only mode, `list`/`today` are `READ` and `create`/`update` are
`WRITE` (local operations).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `FileNotFoundError: Google Calendar credentials not found` | Run `uv run assistant google-auth` to complete the OAuth flow |
| `google.auth.exceptions.RefreshError` | Refresh token expired or revoked — re-run `uv run assistant google-auth` |
| `GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set` | Add both to `.env` (no `ASSISTANT_` prefix) |
| Events only from primary calendar | Check that other calendars are shared to the assistant's Google account |
| `403 Forbidden` from Calendar API | Calendar API not enabled in Google Cloud Console, or consent screen not configured |
| `access_denied` during OAuth flow | Add your Gmail address as a test user in the OAuth consent screen |
| Token file permissions | `data/google_auth/credentials.json` should be readable only by you (`chmod 600`) |

---

## Falling back to SQLite

Set `ASSISTANT_GOOGLE_CALENDAR_ENABLED=false` (or remove it) to revert to
the local SQLite calendar. Both backends use the same tool name (`calendar`)
and actions — the switch is transparent.

---

## Docker notes

Mount the credentials directory so the token persists across container
restarts:

```yaml
volumes:
  - ./data/google_auth:/app/data/google_auth

environment:
  - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
  - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
  - ASSISTANT_GOOGLE_CALENDAR_ENABLED=true
```

Run the OAuth flow on the host first (`uv run assistant google-auth`), then
start the container — it reuses the saved token.
