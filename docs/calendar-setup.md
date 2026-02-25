# Calendar Integration — Radicale Setup

Self-hosted CalDAV calendar using Radicale. The agent reads/writes events via CalDAV, and you view them natively on macOS/iOS Calendar apps.

## Architecture

- **Radicale** — lightweight CalDAV server (separate Docker service)
- **Agent** — reads/writes via CalDAV protocol (simple HTTP)
- **Apple Calendar** — connects to Radicale via CalDAV account (native support)
- **Google Calendar** — agent polls your ICS feed for conflict checking (read-only)

## Setup

### 1. Create directory structure

```bash
mkdir -p ~/Services/radicale/data
```

### 2. Create Radicale config

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

### 3. Create user credentials

```bash
# install htpasswd if needed: brew install httpd
htpasswd -B -c ~/Services/radicale/users assistant
# enter a password — used by Apple Calendar and the agent
```

### 4. Create `docker-compose.yml`

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

### 5. Start the service

```bash
cd ~/Services/radicale
docker compose up -d
```

### 6. Create a calendar collection

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

## Viewing on macOS / iOS

### Local access

1. **System Settings → Internet Accounts → Add Other Account → CalDAV Account**
2. Account Type: **Manual**
3. Username: `assistant`
4. Password: (from step 3)
5. Server Address: `http://localhost:5232`

### Remote access (iOS / off-network)

If you already have Nginx Proxy Manager and a Cloudflare tunnel, add a proxy host:

- Domain: `cal.yourdomain.com`
- Forward to: `radicale:5232` (same `npm-shared` Docker network)
- Enable SSL

Then use `https://cal.yourdomain.com` as the server address on iOS.

Radicale handles authentication via htpasswd — all requests require valid credentials.

### iOS sync via iCloud

If both your Mac and iPhone use the same iCloud account, the CalDAV account added on macOS may sync automatically. Otherwise, repeat the steps on iOS at **Settings → Calendar → Accounts → Add Account → Other → CalDAV**.

## Agent configuration

Add to the assistant's `.env`:

```bash
ASSISTANT_CALDAV_URL=http://radicale:5232/assistant/calendar/
ASSISTANT_CALDAV_USERNAME=assistant
ASSISTANT_CALDAV_PASSWORD=<password>
```

The agent uses standard CalDAV operations:
- `GET` — list/read events
- `PUT` — create or update events
- `DELETE` — remove events

The `caldav` Python library simplifies this further.

## Google Calendar visibility (read-only)

To let the agent check your existing Google Calendar for conflicts:

1. In Google Calendar → Settings → (your calendar) → **Secret address in iCal format**
2. Copy the URL and add to `.env`:
   ```bash
   ASSISTANT_GOOGLE_ICAL_URL=https://calendar.google.com/calendar/ical/...
   ```
3. The agent periodically fetches and parses this ICS feed — no OAuth required (the URL acts as a secret token)
