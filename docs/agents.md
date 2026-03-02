# Agents

Agents are specialized sub-assistants that can be delegated tasks. Each agent has its own system prompt, tool whitelist, and tool-round budget.

## Configuration

Enable agents:

```bash
ASSISTANT_AGENTS_ENABLED=true
```

---

## Defining Agents

Create YAML files in `data/agents/`:

```yaml
# data/agents/researcher.yaml
name: researcher
description: Research agent — searches the web and reads files to gather information.
system_prompt: |
  You are a research assistant. Your job is to gather information and provide
  comprehensive, well-sourced answers.
allowed_tools:
  - web_search
  - http_request
  - read_file
  - memory_search
max_tool_rounds: 50
```

---

## Agent Fields

| Field | Description |
|-------|-------------|
| `name` | Unique identifier |
| `display_name` | Human-friendly name (e.g., "Nova") — defaults to `name.title()` |
| `tagline` | Short descriptor (e.g., "the internet sleuth") |
| `description` | What the agent does |
| `system_prompt` | Agent-specific instructions |
| `allowed_tools` | Whitelist of tools (empty = all tools) |
| `denied_tools` | Blacklist of tools (used when allowed_tools is empty) |
| `allowed_skills` | Whitelist of skills to include in system prompt (empty = no skills, omit = all skills) |
| `model` | LLM model override (`provider/model` syntax) |
| `max_tool_rounds` | Max tool calls per task (default: 5) |
| `vision` | Override vision detection (`true`/`false`, omit for auto-detect from model) |
| `can_delegate` | Allow agent to delegate to other agents (default: false) |

---

## Per-Agent Model Override

Each agent can run on a different LLM by setting the `model` field using `provider/model` syntax:

```yaml
# data/agents/researcher.yaml
name: researcher
description: Research agent
system_prompt: ...
allowed_tools:
  - web_search
  - http_request
  - read_file
model: openai/gpt-4o        # ← runs on OpenAI instead of the default provider
max_tool_rounds: 8
```

Supported provider prefixes:

| Prefix | Provider | Example |
|--------|----------|---------|
| `claude/` | Anthropic Claude | `claude/claude-sonnet-4-20250514` |
| `openai/` | OpenAI | `openai/gpt-4o` |
| `gemini/` | Google Gemini | `gemini/gemini-2.0-flash` |
| `ollama/` | Ollama (local) | `ollama/llama3` |
| `bedrock/` | AWS Bedrock | `bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0` |

If `model` is empty or omitted, the agent uses the default provider. If you omit the `provider/` prefix, the configured default provider is used with the given model name.

---

## How It Works

The main assistant can delegate tasks to agents using the `delegate_to_agent` or `delegate_parallel` tools. Agents run in isolated contexts with scoped tools and cannot delegate to other agents.

---

## Background Delegation

For long-running tasks like deep research, agents can run in the background so you can keep chatting:

```
You: Research the latest advances in quantum computing — do it in the background
```

The assistant sets `background=true` on the `delegate_to_agent` tool, which returns immediately with a task ID. When the agent finishes, the result is delivered asynchronously to the originating channel (CLI, Telegram, or WhatsApp).

Background agents use auto-approved permissions, so they can only use tools whitelisted in their agent YAML. Don't give background agents write tools unless you trust them.

### Checking Background Tasks

```
/tasks                   # List all background tasks with status
/tasks result <id>       # Show the full result of a specific task
```

The LLM can also check task status using the `task_status` tool.

Tasks are stored in memory (up to 50). They do not persist across restarts.

---

## Example Agents

The `data.example/agents/` directory includes these agent templates:

| Agent | Description | Tools |
|-------|-------------|-------|
| **coder** | Read, write, and execute code | shell_exec, read_file, write_file |
| **web_researcher** | Search the web and fetch sources | web_search, web_fetch, http_request |
| **academic_researcher** | Find and analyze academic papers | arxiv_search, web_fetch, read_file |
| **journalist** | Monitor news sources and post digests | hackernews, reddit_search, web_fetch, post_to_feed |
| **image_analyst** | Analyze images with vision models | read_file, write_file |
| **long_text_reader** | Process large documents | read_file, web_fetch |
| **research_coordinator** | Orchestrate multi-agent research | delegate_to_agent, delegate_parallel |

---

## Agentic Agent Management

The assistant can create, edit, and delete agents through conversation using the `manage_agent` tool — no need to hand-edit YAML.

### Examples

```
You: Create an agent called "summarizer" that summarizes long documents.
     Give it read_file and web_search, use openai/gpt-4o-mini, max 8 tool rounds.

You: Edit the researcher agent to also have access to shell_exec

You: What agents do I have?

You: Delete the old summarizer agent
```

Create and edit operations require approval. The YAML files are saved to `data/agents/` and reloaded automatically.

### CLI Commands

```
/agents              # List all agents
/agents reload       # Reload agent definitions
```
