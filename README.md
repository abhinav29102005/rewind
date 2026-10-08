<p align="center">
  <h1 align="center">🔄 Rewind</h1>
  <p align="center">
    <strong>An enforced approval and undo layer for AI agents</strong>
  </p>
  <p align="center">
    Prompts are advice. Rewind makes irreversible actions <b>require approval and stay reversible</b> — outside the agent's control.
  </p>
  <p align="center">
    <a href="#one-command-install">Install</a> •
    <a href="#how-it-works">How It Works</a> •
    <a href="#connect-to-your-agent">Connect to Your Agent</a> •
    <a href="#features">Features</a> •
    <a href="#cli-reference">CLI Reference</a> •
    <a href="#policy-packs">Policies</a> •
    <a href="#contributing">Contributing</a>
  </p>
</p>

---

> **Status:** Prototype / Actively Developed  
> **License:** Apache-2.0

## The Problem

Autonomous AI agents (Cursor, Claude Code, Replit Agent, etc.) are routinely given real credentials and real infrastructure access. When they make a destructive mistake — and [they do](#real-incidents) — nothing in the stack stops them.

Instructions in the agent's prompt are **advisory**, not enforceable.

### Real Incidents

| Incident | What Happened |
|---|---|
| **PocketOS** (Apr 2026) | A Cursor agent deleted a production database and its backups in ~9 seconds, using an API token found in an unrelated file. |
| **DataTalks.Club** (Mar 2026) | A Claude Code agent deleted the production database while trying to clean up duplicates it had mistakenly created. |
| **Replit** (Jul 2025) | An agent wiped data for 1,200+ executives and 1,190 companies during a "code and action freeze" meant to prevent this. |

The Centre for Long-Term Resilience logged **698 cases** (Oct 2025 – Mar 2026) of agents taking covert, deceptive, or unrequested actions.

---

## One-Command Install

```bash
curl -fsSL https://raw.githubusercontent.com/abhinav29102005/rewind/main/install.sh | bash
```

The installer will:
1. ✅ Check Python ≥ 3.11
2. ✅ Install `uv` if missing
3. ✅ Clone the repo (or use your local copy)
4. ✅ Install all dependencies
5. ✅ Configure your AI agent (Claude Desktop, Cursor, or Windsurf)

Or install manually:

```bash
git clone https://github.com/abhinav29102005/rewind.git
cd rewind
uv sync
```

---

## How It Works

Rewind runs as an **MCP (Model Context Protocol) server** that sits between your AI agent and your system. The agent uses Rewind's tools instead of running commands directly.

```
Agent ──► Rewind MCP Server ──► Classify ──► [safe]         → execute + log
                │                        └──► [reversible]   → snapshot → execute + log
                │                        └──► [irreversible] → BLOCK → ask user in chat
                │                                                  │
          Credential Broker                             approved → execute + log
          (agent never sees tokens)                     denied   → block + log
```

### In the Chat (No Separate UI Needed)

When the agent tries something dangerous:

1. 🚫 **Rewind blocks it** and tells the agent to ask you
2. 💬 **The agent asks you** in the chat: *"I need to delete these files. Do you approve?"*
3. ✅ **You reply "yes"** — the agent approves and executes it
4. 📸 **Everything is logged** with cryptographic integrity

No web dashboards. No extra windows. It all happens in your existing chat.

---

## Connect to Your Agent

### Claude Desktop

```bash
bash install.sh   # Select option 1
```

Or manually add to `~/.config/Claude/claude_desktop_config.json` (Linux) / `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "rewind-guard": {
      "command": "uv",
      "args": ["--directory", "/path/to/rewind", "run", "rewind-mcp"]
    }
  }
}
```

### Cursor

```bash
bash install.sh   # Select option 2
```

Or add to your Cursor MCP config or a `.cursor/mcp.json` in any project root.

### Windsurf

```bash
bash install.sh   # Select option 3
```

### Any MCP Client

Rewind is a standard MCP server. Any client that speaks MCP can connect. See [docs/integrations/any-mcp-client.md](docs/integrations/any-mcp-client.md) for the full tool reference.

---

## Features

| Feature | Description |
|---|---|
| 🔐 **Credential Broker** | Agent never sees raw production tokens. Rewind holds them and exposes scoped, short-lived capabilities. |
| 🏷️ **Action Classification** | Every tool call is classified as `safe`, `reversible`, or `irreversible` with explainable reasons. |
| ✋ **In-Chat Approval** | Irreversible actions pause and the agent asks you directly in the chat. No external approval flow needed. |
| 📸 **Snapshots & Rollback** | Automatic git checkpoints before risky operations. Preview diffs and one-command restore. |
| 📋 **Tamper-Evident Audit Log** | Cryptographically chained log of every action, approval, and rollback. |
| 🔌 **Universal MCP Server** | Works with Claude Desktop, Cursor, Windsurf, and any MCP-compatible agent. |

## MCP Tools Exposed

| Tool | What It Does |
|------|--------------|
| `execute_command` | Run a shell command through the guardrail pipeline |
| `approve_request` | Approve a blocked action directly from the chat |
| `execute_approved_command` | Execute an approved action with cryptographic verification |
| `preview_rollback` | Preview the diff before restoring a snapshot |
| `rollback_snapshot` | Restore filesystem state to a checkpoint |

---

## CLI Reference

```bash
uv run rewind --help                    # Show all commands
uv run rewind-mcp                       # Start the MCP guardrail server

# Policy inspection
uv run rewind policy list               # Show loaded policy packs
uv run rewind policy test --tool shell "rm -rf /"    # Test classification

# Session management
uv run rewind session start             # Start a new guarded session
uv run rewind session list              # List active sessions
uv run rewind session end <id>          # End a session

# Rollback
uv run rewind rollback <path>           # Restore a path from snapshot

# Admin
uv run rewind admin create-user --username <name> --role admin
uv run rewind admin list-users
```

---

## Policy Packs

Rewind ships with built-in classification rules for:

| Pack | Covers | Examples |
|------|--------|----------|
| **filesystem** | Shell & file operations | `rm -rf`, `shred`, `mkfs`, `chmod 777` |
| **postgresql** | SQL statements | `DROP TABLE`, `TRUNCATE`, `DELETE` without `WHERE` |
| **git** | Git operations | `git push --force`, `git reset --hard`, `git clean -fd` |
| **aws_s3** | AWS S3 operations | `s3 rm --recursive`, bucket deletion |
| **docker** | Container operations | `docker rm`, `docker system prune`, `docker rmi` |

All packs are YAML files in [`policies/`](policies/) and are fully customizable.

```bash
# Test any command against the policy engine
uv run rewind policy test --tool shell "docker system prune --all --force"
# → Risk: IRREVERSIBLE
# → Reason: System prune removes all unused containers, images, and networks
```

---

## What Makes Rewind Different

Most guardrail tools are **cooperative** — the agent is told to route actions through the guard. A confused or prompt-injected agent can skip it. Rewind is different:

- **Non-bypassable by construction** — the agent has no direct path or credential to production
- **Credential isolation at the infrastructure layer**, not only the command layer
- **One policy and rollback model across tools** — databases, cloud APIs, MCP tools, filesystems
- **Native chat overlay** — no separate dashboards; approval happens in your existing workflow

## Honest Limitations

- **Not a substitute for basic hygiene** — separate prod/staging, least-privilege tokens remain essential
- **Not prevention of bad judgement** — we contain damage; we don't make the agent smarter
- **Not complete rollback** — emails, payments, external API effects cannot be undone
- **Cannot protect what bypasses it** — anything with direct credentials outside Rewind is unprotected

---

## Project Structure

```
rewind/
├── install.sh                 # One-command installer
├── pyproject.toml             # Package config (entry points: rewind, rewind-mcp)
├── policies/                  # YAML policy packs (filesystem, sql, git, aws, docker)
├── src/rewind/
│   ├── mcp_server.py          # FastMCP server — the core MCP integration
│   ├── cli.py                 # Click-based CLI
│   ├── contracts.py           # ActionRequest, RiskClass, action_hash
│   ├── config/                # Config loader, models, defaults
│   ├── policy/                # Classification engine & matchers
│   ├── audit/                 # Tamper-evident audit log
│   ├── snapshot/              # Git snapshotter & rollback
│   ├── team/                  # Multi-user approval system (store, RBAC, sessions)
│   └── proxy/                 # MCP & shell proxies
├── tests/                     # Test suite
├── docs/integrations/         # Per-agent setup guides
├── frontend/                  # Landing page (React + Vite)
└── vscode-extension/          # VS Code approval UI
```

---

## Contributing

We welcome contributions! Whether it's new policy packs, agent adapters, or core improvements.

```bash
git clone https://github.com/abhinav29102005/rewind.git
cd rewind
uv sync
uv run pytest                  # Run tests
uv run ruff check src/         # Lint
```

See [PLAN.md](PLAN.md) for the roadmap.

## License

Apache-2.0

---

<p align="center">
  <i>Turning 9-second database deletions into recoverable events.</i>
</p>
