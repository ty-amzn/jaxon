# Runbook: Cloudflare Access (Zero Trust) for the Assistant API

## Overview

Cloudflare Access puts authentication in front of your tunnel so only authorized users can reach the assistant API and feed UI. Auth happens at the Cloudflare edge — no code changes needed.

| Method | Description |
|--------|-------------|
| **One-time PIN** | Email OTP — no third-party IdP required |
| **Google / GitHub / etc.** | OAuth SSO via identity provider |
| **Service Token** | Machine-to-machine (for API/webhook callers) |

---

## Prerequisites

- A Cloudflare account with a domain (free plan works)
- A running Cloudflare Tunnel pointing to `localhost:51430`
- The tunnel is assigned a hostname (e.g. `assistant.yourdomain.com`)

If you don't have a tunnel yet:

```bash
# Install cloudflared
brew install cloudflared        # macOS
# or: sudo apt install cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create assistant

# Route DNS
cloudflared tunnel route dns assistant assistant.yourdomain.com

# Run it
cloudflared tunnel --url http://localhost:51430 run assistant
```

---

## Step 1 — Open the Zero Trust Dashboard

1. Go to [https://one.dash.cloudflare.com](https://one.dash.cloudflare.com)
2. Select your account
3. You'll land in the **Zero Trust** section

---

## Step 2 — Configure an Identity Provider

1. Navigate to **Settings → Authentication → Login methods**
2. Click **Add new** and choose a method:
   - **One-time PIN** (simplest — already enabled by default, uses email OTP)
   - **Google** — provide OAuth client ID + secret
   - **GitHub** — provide OAuth app credentials
3. Click **Save**

For personal use, **One-time PIN** is the easiest — just enter your email, get a code, done.

---

## Step 3 — Create an Access Application

1. Navigate to **Access → Applications**
2. Click **Add an application** → **Self-hosted**
3. Fill in:
   - **Application name:** `Assistant`
   - **Session duration:** `24 hours` (or your preference)
   - **Application domain:** `assistant.yourdomain.com`
     - To protect only the feed: set **Path** to `/feed`
     - Leave path empty to protect everything
4. Click **Next**

---

## Step 4 — Add an Access Policy

1. **Policy name:** `Allow me`
2. **Action:** `Allow`
3. **Include rule:**
   - **Selector:** `Emails`
   - **Value:** `your-email@example.com`
4. Click **Next** → **Add application**

You can add multiple rules:
- Specific emails
- Email domains (e.g. `@yourcompany.com`)
- GitHub organizations
- IP ranges (e.g. home IP as a bypass)

---

## Step 5 — Verify

1. Open `https://assistant.yourdomain.com/feed/ui` in an incognito window
2. You should see the Cloudflare Access login page
3. Authenticate with your configured method
4. After login you'll see the feed UI
5. The session persists for the configured duration

---

## Optional: Bypass Auth for Specific Paths

If you need webhooks or health checks accessible without auth:

1. Create a second Access Application for the specific path
2. Set the **Action** to `Bypass`

| Path | Policy |
|------|--------|
| `assistant.yourdomain.com` | Allow (email) |
| `assistant.yourdomain.com/health` | Bypass |
| `assistant.yourdomain.com/webhooks/*` | Bypass or Service Token |

---

## Optional: Service Tokens (for API/Webhook Callers)

For machine-to-machine access (e.g. external services calling webhooks):

1. Navigate to **Access → Service Auth → Service Tokens**
2. Click **Create Service Token**
3. Copy the **Client ID** and **Client Secret**
4. Callers include these headers in requests:

```bash
curl https://assistant.yourdomain.com/webhooks/my-hook \
  -H "CF-Access-Client-Id: <client-id>" \
  -H "CF-Access-Client-Secret: <client-secret>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Troubleshooting

### "Access denied" after login
- Check the policy includes your email (exact match, case-sensitive)
- Verify the application domain matches your tunnel hostname exactly

### Tunnel not reachable
- Confirm `cloudflared` is running: `cloudflared tunnel info assistant`
- Check DNS: `dig assistant.yourdomain.com` should return Cloudflare IPs

### Webhook callers blocked
- Add a Bypass policy for the webhook path, or use a Service Token
- Ensure the `CF-Access-Client-Id` and `CF-Access-Client-Secret` headers are sent

### Session expires too quickly
- Edit the application → increase **Session duration** (up to 30 days)
