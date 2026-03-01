# Scheduler, File Monitoring & DND

## Scheduler

Schedule reminders and automated tasks using natural language or the API.

### Configuration

```bash
ASSISTANT_SCHEDULER_ENABLED=true
ASSISTANT_SCHEDULER_TIMEZONE=UTC
```

### Natural Language Reminders

Just ask the assistant:

```
You: Remind me at 9am tomorrow to review the PRs
```

### Managing Jobs

```
/schedule list           # See all scheduled jobs
/schedule remove <id>    # Remove a job
```

### Trigger Types

- **date** — One-time at a specific datetime
- **cron** — Recurring on a cron schedule
- **interval** — Recurring at fixed intervals

Jobs persist across restarts in `data/db/scheduler.db`.

---

## File Monitoring

Watch directories for changes and get notified.

### Configuration

```bash
ASSISTANT_WATCHDOG_ENABLED=true
ASSISTANT_WATCHDOG_PATHS=/path/to/watch,/another/path
ASSISTANT_WATCHDOG_DEBOUNCE_SECONDS=2.0
ASSISTANT_WATCHDOG_ANALYZE=false    # Set true to analyze changes with the assistant
```

### CLI Commands

```
/watch                   # Show status
/watch add <path>        # Watch a directory
/watch remove <path>     # Stop watching
```

---

## Workflows

Multi-step automation chains defined in YAML.

### Creating a Workflow

Create a `.yaml` file in `data/workflows/`:

```yaml
name: daily-summary
description: Generate and send a daily summary
trigger: manual        # "manual", "webhook", or "schedule"
enabled: true
steps:
  - name: gather-data
    tool: shell_exec
    args:
      command: "cat /tmp/today-notes.txt"

  - name: review-results
    tool: read_file
    args:
      path: "/tmp/review.md"
    requires_approval: true
```

### Step Execution

- Steps run sequentially; each step's output is available to the next
- Steps with `requires_approval: true` pause for user confirmation
- Execution stops on the first error

### CLI Commands

```
/workflow list           # List all workflows
/workflow run <name>     # Run a workflow
/workflow reload         # Reload YAML definitions
```

---

## Do Not Disturb

Suppress non-urgent notifications during specified hours.

### Configuration

```bash
ASSISTANT_DND_ENABLED=true
ASSISTANT_DND_START=23:00       # HH:MM
ASSISTANT_DND_END=07:00
ASSISTANT_DND_ALLOW_URGENT=true
```

During the DND window, non-urgent notifications are queued and delivered when the window ends. Urgent notifications bypass DND when `allow_urgent` is enabled.

---

## Backups

Create and restore snapshots of all assistant data.

### CLI Commands

```
/backup create [name]     # Create (default name: "backup")
/backup list              # List available backups
/backup restore <name>    # Restore from backup
```

Backups are `.tar.gz` files in `data/backups/`. They include all data: memory, threads, skills, databases, and logs.
