# Features

## Slash Commands

Type `/help` in the chat to see all available commands.

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Show session status |
| `/memory` | View or update durable memory |
| `/history <query>` | Search conversation history |
| `/cancel` | Cancel current operation |
| `/config` | View current configuration |
| `/skills` | List available skills |
| `/skills <name>` | Show skill details |
| `/skills reload` | Reload skills from disk |
| `/thread` | Show current thread status |
| `/thread new <name>` | Create new thread |
| `/thread save` | Save current conversation |
| `/thread load <name>` | Load a saved thread |
| `/thread list` | List all saved threads |
| `/thread export <fmt>` | Export thread (json/markdown) |
| `/thread delete <id>` | Delete a thread |
| `/clear session` | Clear current session messages |
| `/clear history` | Delete all daily log files |
| `/clear memory` | Wipe durable memory (MEMORY.md) |
| `/clear search` | Clear FTS5 index and embeddings |
| `/clear all` | All of the above |
| `/schedule list` | List scheduled jobs |
| `/schedule remove <id>` | Remove a scheduled job |
| `/watch` | Manage filesystem monitoring |
| `/workflow list` | List all workflows |
| `/workflow run <name>` | Run a workflow |
| `/workflow reload` | Reload workflow definitions |
| `/webhook list` | List webhook endpoints |
| `/webhook test <name>` | Test a webhook endpoint |
| `/backup create [name]` | Create a data backup |
| `/backup list` | List available backups |
| `/backup restore <name>` | Restore from backup |
| `/plugins` | Manage plugins |
| `/agents` | List available agents |
| `/tasks` | List background agent tasks |
| `/tasks result <id>` | Show result of a background task |

All `/clear` subcommands prompt for confirmation before executing.

---

## Personality & Identity

The assistant's personality is defined in `data/memory/IDENTITY.md` and loaded into every conversation's system prompt.

### Changing Through Chat

Just tell the assistant how you want it to behave:

```
You: Be more casual and use humor
You: Talk like a friendly colleague, not a robot
You: Be formal and extremely concise
You: Your name is Jarvis
```

The assistant uses the `update_identity` tool to read the current identity, modify it based on your request, and save it. Write operations require your approval.

### Manual Editing

You can also edit `data/memory/IDENTITY.md` directly. Changes take effect on the next message.

---

## Memory System

The assistant has persistent memory across sessions.

### Identity

`data/memory/IDENTITY.md` defines the assistant's personality and role. Set up during onboarding or updated via chat.

### Durable Memory

`data/memory/MEMORY.md` stores long-term facts and preferences (your name, preferences, key facts). The assistant can update this during conversation, or you can manage it manually:

```
/memory                  # View current memory
/memory append <text>    # Add to memory
```

### Daily Logs

Conversations are automatically logged to `data/memory/daily/` with one file per day, providing a full history of interactions.

### Full-Text Search

All messages are indexed in a SQLite FTS5 database for fast keyword search:

```
/history authentication   # Search past conversations
```

### Clearing Data

Use the `/clear` command to reset specific data:

```
/clear session    # Reset current conversation
/clear history    # Delete all daily logs
/clear memory     # Wipe MEMORY.md
/clear search     # Clear search index and embeddings
/clear all        # Everything
```

---

## Agentic Memory

The assistant can search, recall, and forget its own memories through LLM-callable tools.

### Searching

The assistant automatically uses `memory_search` when you ask about past conversations:

```
You: What did we discuss about authentication last week?
You: Have I mentioned any deadlines?
You: What do you know about me?
```

The tool searches across durable memory, FTS5 history, and daily logs.

### Forgetting

Ask the assistant to forget specific information:

```
You: Forget about the old project notes
You: Delete all memories about the test data
You: Forget everything (wipe all memory)
```

The `memory_forget` tool handles deletion. It requires your approval since it's a destructive action. When forgetting a topic, it removes matching lines from MEMORY.md and matching rows from the search index.

---

## Skills

Skills are markdown files that inject specialized instructions into the assistant's system prompt.

### Creating a Skill

Create a `.md` file in `data/skills/`:

```markdown
# Code Review

When asked to review code, follow this approach:

## 1. Security Review
- Check for SQL injection
- Look for XSS vulnerabilities

## 2. Performance
- Identify N+1 queries
- Check for unnecessary allocations
```

### Managing Skills

```
/skills              # List all skills
/skills code-review  # View a specific skill
/skills reload       # Reload after adding/editing files
```

Skills are loaded automatically at startup and injected into every conversation.

---

## Agentic Skill Management

The assistant can create, edit, and delete skills through conversation using the `manage_skill` tool.

### Examples

```
You: Create a skill for summarizing emails — include TL;DR, key points, and action items
You: Edit the code-review skill to also check for accessibility issues
You: What skills do I have?
You: Delete the old summarizer skill
```

Create and edit operations require approval. The skill files are saved to `data/skills/` and reloaded automatically.

---

## Conversation Threading

Save, load, and export conversation threads for organized multi-session work.

### Workflow

```
/thread new api-design    # Start a named thread
# ... have a conversation ...
/thread save              # Save it

# Later...
/thread list              # See all threads
/thread load api-design   # Resume where you left off
```

### Exporting

```
/thread export json       # Machine-readable export
/thread export markdown   # Human-readable export
```

Threads are stored as JSON files in `data/threads/`.

---

## Image Support

Send images to vision-capable models using the `@image:` syntax.

### Usage

```
What's in this image? @image:/path/to/screenshot.png

Compare these designs:
@image:/path/design-v1.png
@image:/path/design-v2.png
```

### Supported Formats

PNG, JPEG, GIF, WebP — up to 10 MB per image (configurable via `ASSISTANT_MAX_MEDIA_SIZE_MB`).

### Requirements

Works with Claude (Sonnet/Opus) and vision-capable Ollama models (e.g., `llava`).

---

## Security

### Input Sanitization

All tool inputs are automatically sanitized before execution:

- **Prompt injection patterns** are stripped — system prompt markers, role-play attempts, and instruction overrides
- **File paths** are sanitized to prevent directory traversal
- Applied at a single chokepoint (`ToolRegistry.execute()`) so all tools benefit automatically

### Permission Gates

Every tool call goes through the permission system. Destructive or sensitive operations require explicit user approval before execution.

### Audit Logging

All tool calls (approved, denied, and errors) are logged to `data/logs/audit.jsonl` with timestamps, inputs, outputs, and duration.

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
