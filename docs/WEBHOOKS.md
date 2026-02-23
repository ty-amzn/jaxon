# Webhooks Guide

Trigger workflows from external services (GitHub, CI/CD, monitoring, etc.) via HTTP POST requests with optional HMAC-SHA256 signature verification.

---

## Setup

### 1. Enable webhooks

```bash
# .env
ASSISTANT_WEBHOOK_ENABLED=true
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

```bash
curl -X POST http://localhost:51430/webhooks/deploy-notify \
  -H "Content-Type: application/json" \
  -d '{"ref": "refs/heads/main", "status": "success"}'
```

### With HMAC-SHA256 signature

```bash
# .env
ASSISTANT_WEBHOOK_SECRET=my-secret-key
```

```bash
SECRET="my-secret-key"
PAYLOAD='{"ref": "refs/heads/main", "status": "success"}'
SIGNATURE="sha256=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')"

curl -X POST http://localhost:51430/webhooks/deploy-notify \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: $SIGNATURE" \
  -d "$PAYLOAD"
```

---

## HMAC-SHA256 Validation

When `ASSISTANT_WEBHOOK_SECRET` is set, every incoming request must include a valid `X-Hub-Signature-256` header. This is compatible with GitHub's webhook signature format.

### How it works

1. The sender computes `sha256=HMAC-SHA256(secret, raw_body)` and sends it in the `X-Hub-Signature-256` header
2. The assistant recomputes the HMAC over the raw request body using the configured secret
3. Signatures are compared using `hmac.compare_digest()` (constant-time comparison to prevent timing attacks)

### Response codes

| Status | Meaning |
|--------|---------|
| `200` | Webhook accepted and workflow executed |
| `401` | Missing `X-Hub-Signature-256` header (when secret is configured) |
| `403` | Invalid signature |
| `404` | No workflow found with that name |
| `409` | Workflow exists but is disabled |
| `503` | Workflow system not initialized |

### No secret configured

If `ASSISTANT_WEBHOOK_SECRET` is empty (the default), signature validation is skipped entirely and all requests are accepted. This is fine for local development but not recommended for production.

---

## GitHub Integration

GitHub webhooks are natively compatible since the assistant uses the same `X-Hub-Signature-256` header format.

### 1. Create a workflow for GitHub events

```yaml
# data/workflows/github-push.yaml
name: github-push
description: Handle GitHub push events
trigger: webhook
enabled: true
steps:
  - name: log-push
    tool: shell_exec
    args:
      command: "echo 'Push to repository received'"
```

### 2. Configure the GitHub webhook

In your GitHub repository: **Settings > Webhooks > Add webhook**

| Field | Value |
|-------|-------|
| Payload URL | `https://your-server:51430/webhooks/github-push` |
| Content type | `application/json` |
| Secret | Same value as `ASSISTANT_WEBHOOK_SECRET` |
| Events | Choose which events to receive |

### 3. Access the payload

The JSON body from GitHub is passed as the workflow's `context` and merged into each step's `args`. For example, to access the repository name in a shell step:

```yaml
steps:
  - name: log-repo
    tool: shell_exec
    args:
      command: "echo 'Event from repository'"
```

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

### Example output

```
/webhook list

Webhooks:
  POST /webhooks/deploy-notify  [enabled]
  POST /webhooks/github-push    [enabled]
  POST /webhooks/old-hook       [disabled]
```

```
/webhook test deploy-notify

Testing webhook: deploy-notify
Response: 200 OK
{"status": "ok", "workflow": "deploy-notify", "results": [...]}
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
| `ASSISTANT_WEBHOOK_SECRET` | `""` | HMAC-SHA256 secret (empty = no validation) |
| `ASSISTANT_HOST` | `127.0.0.1` | API server bind address |
| `ASSISTANT_PORT` | `51430` | API server port |

---

## Troubleshooting

### Webhook returns 404

- Verify the workflow name matches the URL path: `/webhooks/{name}` maps to `data/workflows/{name}.yaml`
- Run `/webhook list` to see loaded workflows
- Try `/workflow reload` then `/webhook list` again

### Webhook returns 401/403

- Check that `ASSISTANT_WEBHOOK_SECRET` matches the sender's secret exactly
- Ensure the sender is computing the signature over the raw body (not a re-serialized version)
- The header must be `X-Hub-Signature-256`, not `X-Hub-Signature`

### Webhook returns 503

- The workflow system hasn't initialized — wait for the server to fully start
- Check `data/logs/app.log` for startup errors

### Workflow doesn't run

- Verify the workflow has `enabled: true`
- Check that the workflow's `trigger` field is set to `webhook` (though any trigger type will work when called via the webhook endpoint)
- Look at `data/logs/audit.jsonl` for tool execution logs
