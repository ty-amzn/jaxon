# Google Calendar

The assistant can read and write events via the **Google Calendar API v3**. When enabled, the existing `calendar` tool switches from the local SQLite backend to Google Calendar — no tool schema changes needed.

| Feature | How it works |
|---------|--------------|
| **Read events** | Queries all calendars visible to the Google account (primary + shared) |
| **Create / update / delete** | Writes to the primary calendar |
| **Shared calendars** | Share other calendars *into* the Google account — they appear automatically |
| **macOS / iOS sync** | Add the Google account in System Settings → Internet Accounts; events show up in Apple Calendar |

Authentication uses OAuth2 with a Desktop app flow. A refresh token is saved locally so the assistant can act on your behalf without re-prompting.

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

This opens a browser for Google consent. Sign in with the Gmail account the assistant should use, grant Calendar access, and the CLI saves the refresh token to `data/google_auth/credentials.json`.

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

Check Apple Calendar — new events should appear within seconds (Google sync push is near-instant to connected Apple devices).

---

## Shared calendars

The assistant reads from **all calendars** visible to the Google account, not just the primary one. To give it visibility into other calendars:

1. From the other Google account, go to [Google Calendar settings](https://calendar.google.com/calendar/r/settings).
2. Click the calendar → **Share with specific people**.
3. Add the assistant's Gmail address.
4. Choose permission level:
   - **See all event details** — read-only.
   - **Make changes to events** — if the assistant should be able to modify events on that calendar.

Shared calendars appear automatically — no `add_feed` action needed. The `.ics` feed actions (`add_feed`, `remove_feed`, `sync_feeds`) return a message explaining this when Google mode is active.

---

## Permissions

When Google Calendar is enabled, tool permissions change because all operations hit the network:

| Action | Permission | Approval needed? |
|--------|-----------|------------------|
| `list`, `today` | `NETWORK_READ` | No (auto-approved) |
| `create`, `update` | `NETWORK_WRITE` | Yes |
| `delete` | `NETWORK_WRITE` | Yes |
| `add_feed`, `remove_feed`, `sync_feeds` | `NETWORK_READ` | No (returns info message) |

In SQLite-only mode, `list`/`today` are `READ` and `create`/`update` are `WRITE` (local operations).

---

## CalDAV / Radicale (Self-Hosted Alternative)

Instead of Google Calendar, you can use a self-hosted CalDAV server (Radicale) for full control over your data.

### Architecture

- **Radicale** — lightweight CalDAV server (separate Docker service)
- **Agent** — reads/writes via CalDAV protocol (simple HTTP)
- **Apple Calendar** — connects to Radicale via CalDAV account (native support)
- **Google Calendar** — agent polls your ICS feed for conflict checking (read-only)

### Setup

#### 1. Create directory structure

```bash
mkdir -p ~/Services/radicale/data
```

#### 2. Create Radicale config

Create `~/Services/radicale/config`:

```ini
[server]
hosts = 0.0.0.0:5232

[auth]
type = htpasswd
htpasswd_filename = /etc/radicale/users
htpasswd_encryption = bcrypt

[storage]
filesystem_folder = /var/lib/radicale/collections

[logging]
level = info
```

#### 3. Create user credentials

```bash
# install htpasswd if needed: brew install httpd
htpasswd -B -c ~/Services/radicale/users assistant
# enter a password — used by Apple Calendar and the agent
```

#### 4. Create `docker-compose.yml`

Create `~/Services/radicale/docker-compose.yml`:

```yaml
services:
  radicale:
    container_name: radicale
    image: tomsquest/docker-radicale
    ports:
      - "5232:5232"
    volumes:
      - ./data:/var/lib/radicale
      - ./config:/etc/radicale/config
      - ./users:/etc/radicale/users
    restart: unless-stopped
    networks:
      - npm-shared

networks:
  npm-shared:
    external: true
    name: npm-shared
```

#### 5. Start the service

```bash
cd ~/Services/radicale
docker compose up -d
```

#### 6. Create a calendar collection

```bash
curl -u assistant:PASSWORD -X MKCALENDAR \
  http://localhost:5232/assistant/calendar/ \
  --data '<?xml version="1.0" encoding="UTF-8"?>
<mkcalendar xmlns="urn:ietf:params:xml:ns:caldav">
  <set xmlns="DAV:">
    <prop>
      <displayname>Assistant</displayname>
    </prop>
  </set>
</mkcalendar>'
```

### Viewing on macOS / iOS

#### Local access

1. **System Settings → Internet Accounts → Add Other Account → CalDAV Account**
2. Account Type: **Manual**
3. Username: `assistant`
4. Password: (from step 3)
5. Server Address: `http://localhost:5232`

#### Remote access (iOS / off-network)

If you already have Nginx Proxy Manager and a Cloudflare tunnel, add a proxy host:

- Domain: `cal.yourdomain.com`
- Forward to: `radicale:5232` (same `npm-shared` Docker network)
- Enable SSL

Then use `https://cal.yourdomain.com` as the server address on iOS.

Radicale handles authentication via htpasswd — all requests require valid credentials.

#### iOS sync via iCloud

If both your Mac and iPhone use the same iCloud account, the CalDAV account added on macOS may sync automatically. Otherwise, repeat the steps on iOS at **Settings → Calendar → Accounts → Add Account → Other → CalDAV**.

### CalDAV Configuration

Add to the assistant's `.env`:

```bash
ASSISTANT_CALDAV_ENABLED=true
ASSISTANT_CALDAV_URL=http://radicale:5232/assistant/calendar/
CALDAV_USERNAME=assistant
CALDAV_PASSWORD=<password>
```

When `ASSISTANT_CALDAV_ENABLED=true`, the calendar tool routes CRUD operations (create, list, today, update, delete) through CalDAV. Feed subscriptions (`add_feed`, `sync_feeds`, `remove_feed`) continue to use the local SQLite store for read-only ICS imports.

### Reminders (VTODO)

When CalDAV is enabled, a separate `reminders` tool is registered that manages VTODO items in the same Radicale calendar collection. VTODOs sync to the iOS Reminders app automatically.

#### Usage examples

```
reminders create title="Buy milk" due="2025-03-15T18:00:00" priority="medium"
reminders list
reminders complete reminder_id="<id>"
reminders update reminder_id="<id>" title="Buy oat milk"
reminders delete reminder_id="<id>"
```

#### VTODO ↔ iOS Reminders mapping

| VTODO field | iOS Reminders | Values |
|---|---|---|
| SUMMARY | Title | free text |
| DUE | Due date | ISO 8601 datetime |
| PRIORITY | Priority | 1 (high), 5 (medium), 9 (low) |
| DESCRIPTION | Notes | free text |
| STATUS | Completion | NEEDS-ACTION / COMPLETED |

### Google Calendar visibility (read-only)

To let the agent check your existing Google Calendar for conflicts:

1. In Google Calendar → Settings → (your calendar) → **Secret address in iCal format**
2. Copy the URL and add to `.env`:
   ```bash
   ASSISTANT_GOOGLE_ICAL_URL=https://calendar.google.com/calendar/ical/...
   ```
3. The agent periodically fetches and parses this ICS feed — no OAuth required (the URL acts as a secret token)

---

## Falling back to SQLite

Set `ASSISTANT_GOOGLE_CALENDAR_ENABLED=false` (or remove it) to revert to the local SQLite calendar. Both backends use the same tool name (`calendar`) and actions — the switch is transparent.

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

## Docker notes

Mount the credentials directory so the token persists across container restarts:

```yaml
volumes:
  - ./data/google_auth:/app/data/google_auth

environment:
  - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
  - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
  - ASSISTANT_GOOGLE_CALENDAR_ENABLED=true
```

Run the OAuth flow on the host first (`uv run assistant google-auth`), then start the container — it reuses the saved token.

---

## YouTube Playlists (Same GCP Project)

The `youtube_playlist` tool uses the same GCP project and OAuth credentials (`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`) but authenticates a **separate Google account** with a separate credential file. This lets you manage YouTube playlists on a different account than your calendar.

### Setup

1. In the same GCP project, enable the **YouTube Data API v3** (APIs & Services → Library).
2. Add the YouTube scope to your OAuth consent screen: `https://www.googleapis.com/auth/youtube`.
3. Add the YouTube Google account as a test user (if the app is in "Testing" status).
4. Run the YouTube auth flow:

```bash
uv run assistant youtube-auth
```

This opens a browser — sign in with the YouTube account (can be different from the Calendar account). The token is saved to `data/google_auth/youtube_credentials.json`.

5. Enable the tool:

```dotenv
ASSISTANT_YOUTUBE_PLAYLIST_ENABLED=true
```

### Actions

| Action | Description | Permission |
|--------|-------------|------------|
| `list_playlists` | List all playlists on the account | `NETWORK_READ` (auto-approved) |
| `list_videos` | List videos in a playlist | `NETWORK_READ` (auto-approved) |
| `add_video` | Add a video to a playlist | `NETWORK_WRITE` (requires approval) |
| `remove_video` | Remove a video from a playlist | `NETWORK_WRITE` (requires approval) |
| `create_playlist` | Create a new playlist | `NETWORK_WRITE` (requires approval) |

### Example prompts

| Prompt | Expected |
|--------|----------|
| "List my YouTube playlists" | Shows all playlists with video counts |
| "Create a playlist called Agent Picks" | Creates a private playlist, returns ID |
| "Add this video to Agent Picks: youtube.com/watch?v=..." | Adds the video to the playlist |
| "What's in the Agent Picks playlist?" | Lists videos with titles and positions |
| "Remove the first video from Agent Picks" | Removes by playlist item ID |

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `FileNotFoundError: YouTube credentials not found` | Run `uv run assistant youtube-auth` |
| `403 Forbidden` from YouTube API | YouTube Data API v3 not enabled in GCP, or YouTube scope not added to consent screen |
| `access_denied` during OAuth | Add the YouTube account as a test user in the OAuth consent screen |
| Token file permissions | `data/google_auth/youtube_credentials.json` should be `chmod 600` |

### Docker

Mount the same `google_auth` directory and add the enable flag:

```yaml
environment:
  - ASSISTANT_YOUTUBE_PLAYLIST_ENABLED=true
```

Run `uv run assistant youtube-auth` on the host first.
