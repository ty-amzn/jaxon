# Webhooks Guide

Trigger workflows from external services (GitHub, IFTTT, iOS Shortcuts, etc.) via HTTP POST requests with bearer token authentication.

---

## Setup

### 1. Enable webhooks

```bash
# .env
ASSISTANT_WEBHOOK_ENABLED=true
# generate with: openssl rand -hex 32
ASSISTANT_WEBHOOK_SECRET=your-secret-token-here
```

### 2. Start the API server

```bash
uv run assistant serve    # default: http://127.0.0.1:51430
```

Webhooks are only available when the API server is running. They are not available in CLI-only mode (`uv run assistant chat`).

### 3. Create a workflow

Webhooks map 1:1 to workflow definitions. Create a YAML file in `data/workflows/`:

```yaml
# data/workflows/deploy-notify.yaml
name: deploy-notify
description: Notify on deployment events
trigger: webhook
enabled: true
steps:
  - name: log-event
    tool: shell_exec
    args:
      command: "echo 'Deployment received'"

  - name: record-in-memory
    tool: memory_store
    args:
      section: "Deployments"
      fact: "Deployment event received"
```

The workflow name becomes the webhook URL path: `POST /webhooks/deploy-notify`.

---

## Sending Webhooks

### Basic request (no authentication)

If `ASSISTANT_WEBHOOK_SECRET` is empty, all requests are accepted (local dev only):

```bash
curl -X POST http://localhost:51430/webhooks/deploy-notify \
  -H "Content-Type: application/json" \
  -d '{"ref": "refs/heads/main", "status": "success"}'
```

### With bearer token

```bash
curl -X POST http://localhost:51430/webhooks/deploy-notify \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-secret-token-here" \
  -d '{"ref": "refs/heads/main", "status": "success"}'
```

### Response codes

| Status | Meaning |
|--------|---------|
| `200` | Webhook accepted and workflow executed |
| `401` | Missing `Authorization` header (when secret is configured) |
| `403` | Invalid token |
| `404` | No workflow found with that name |
| `409` | Workflow exists but is disabled |
| `503` | Workflow system not initialized |

---

## Authentication

When `ASSISTANT_WEBHOOK_SECRET` is set, every request must include a valid `Authorization` header. The token is compared using constant-time comparison to prevent timing attacks.

Accepted formats:
- `Authorization: Bearer <token>` (standard)
- `Authorization: <token>` (raw — for callers that can't set the Bearer prefix)

### Why bearer token instead of HMAC?

Bearer tokens work with every HTTP client — IFTTT, iOS Shortcuts, Zapier, curl, any no-code platform. HMAC requires the caller to compute a signature over the request body, which most platforms can't do. When paired with HTTPS (via Cloudflare Tunnel), the token can't be intercepted and the payload can't be tampered with in transit, giving equivalent security.

### No secret configured

If `ASSISTANT_WEBHOOK_SECRET` is empty (the default), token validation is skipped entirely. This is fine for local development but not recommended for production.

---

## Security Recommendations

### Cloudflare Tunnel (recommended)

If you expose webhooks to the internet, route them through a Cloudflare Tunnel:

1. **HTTPS** — encrypted transport, no self-signed certs
2. **Cloudflare Access** — add a service token policy on `/webhooks/*` for an extra authentication layer before traffic reaches your server
3. **IP allowlisting** — restrict to known source IPs (e.g., GitHub's published ranges) in the tunnel config

This gives you defense in depth: Cloudflare Access authenticates the caller, HTTPS protects the transport, and the bearer token validates at the application level.

### Token generation

```bash
# Generate a secure random token
openssl rand -hex 32
```

Rotate tokens periodically. When you change the secret, update all callers.

---

## IFTTT Integration

1. Create a workflow YAML in `data/workflows/`
2. In IFTTT, create an applet with a **Webhooks** action:
   - URL: `https://your-tunnel-domain/webhooks/your-workflow-name`
   - Method: `POST`
   - Content Type: `application/json`
   - Additional Headers: `Authorization: Bearer your-secret-token-here`
   - Body: whatever JSON payload you want to pass

---

## GitHub Integration

GitHub can send a bearer token via its `Secret` field — but note GitHub uses HMAC natively. For simplicity, you can skip GitHub's secret field and just add the bearer token as a custom header via a proxy, or use Cloudflare Access service tokens for GitHub webhook IPs.

Alternatively, just use a Cloudflare Access policy that allows GitHub's webhook IP ranges.

---

## Workflow Context

The webhook JSON payload is passed as context to the workflow runner. Context values are merged into each step's `args` dict, and the output of each step is available to the next step as `previous_output`.

### Step chaining example

```yaml
name: process-event
description: Multi-step webhook handler
trigger: webhook
enabled: true
steps:
  - name: fetch-details
    tool: http_request
    args:
      method: GET
      url: "https://api.example.com/details"

  - name: analyze
    tool: shell_exec
    args:
      command: "echo 'Processing webhook data'"

  - name: review
    tool: read_file
    args:
      path: "/tmp/review.md"
    requires_approval: true     # pauses for user confirmation
```

---

## Approval Gates

Steps with `requires_approval: true` pause execution until a user approves. This is useful for critical actions triggered by webhooks.

When a webhook triggers a workflow with approval gates:

- The workflow runs up to the approval step and pauses
- A notification is sent via the configured notification channel (Telegram, CLI, etc.)
- The remaining steps run after approval

> **Note:** Approval gates require an active notification channel. In headless/webhook-only mode, approval-gated steps will block indefinitely.

---

## CLI Commands

```
/webhook list            # List all webhook-enabled workflows with URLs
/webhook test <name>     # Send a test POST to a webhook endpoint
```

---

## Notifications

When a webhook triggers a workflow, the results are sent via the `NotificationDispatcher`. If Telegram or WhatsApp is configured, you'll receive a message like:

```
Webhook 'deploy-notify' triggered workflow:
  log-event: success
  record-in-memory: success
```

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ASSISTANT_WEBHOOK_ENABLED` | `false` | Enable webhook endpoints |
| `ASSISTANT_WEBHOOK_SECRET` | `""` | Bearer token (empty = no validation) |
| `ASSISTANT_HOST` | `127.0.0.1` | API server bind address |
| `ASSISTANT_PORT` | `51430` | API server port |

---

## Troubleshooting

### Webhook returns 404

- Verify the workflow name matches the URL path: `/webhooks/{name}` maps to `data/workflows/{name}.yaml`
- Run `/webhook list` to see loaded workflows
- Try `/workflow reload` then `/webhook list` again

### Webhook returns 401/403

- Check that `ASSISTANT_WEBHOOK_SECRET` matches the token sent in the `Authorization` header
- The header format should be `Authorization: Bearer <token>`

### Webhook returns 503

- The workflow system hasn't initialized — wait for the server to fully start
- Check `data/logs/app.log` for startup errors

### Workflow doesn't run

- Verify the workflow has `enabled: true`
- Check that the workflow's `trigger` field is set to `webhook` (though any trigger type will work when called via the webhook endpoint)
- Look at `data/logs/audit.jsonl` for tool execution logs
