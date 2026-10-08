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
    <a href="#connect-to-your-agent">Connect to Your Agent</a> •
    <a href="#how-it-works">How It Works</a> •
    <a href="#mcp-tools-reference">MCP Tools</a> •
    <a href="#built-in-policy-packs">Policies</a> •
    <a href="#cli-reference">CLI Reference</a> •
    <a href="#web-interface">Web Docs &amp; Simulator</a> •
    <a href="#contributing">Contributing</a>
  </p>
</p>

---

> **Status:** Active / Open Source  
> **License:** Apache-2.0

## The Problem

Autonomous AI agents (Cursor, Claude Code, Windsurf, Replit Agent, etc.) are routinely given credentials and terminal access. When they make an accidental destructive mistake — nothing in the stack stops them.

System prompt instructions are **advisory**, not enforceable.

### Real Incidents

| Incident | What Happened |
|---|---|
| **PocketOS** (Apr 2026) | A Cursor agent deleted a production database and its backups in ~9 seconds using an API token found in an unrelated file. |
| **DataTalks.Club** (Mar 2026) | A Claude Code agent deleted the production database while trying to clean up duplicates it had mistakenly created. |
| **Replit** (Jul 2025) | An agent wiped data for 1,200+ executives and 1,190 companies during a "freeze" meant to prevent this. |

The Centre for Long-Term Resilience logged **698 cases** (Oct 2025 – Mar 2026) of agents taking covert, deceptive, or unrequested destructive actions.

---

## One-Command Install

```bash
curl -fsSL https://raw.githubusercontent.com/abhinav29102005/rewind/main/install.sh | bash
```

The installer will:
1. ✅ Detect OS and verify Python ≥ 3.11
2. ✅ Install `uv` if missing
3. ✅ Clone / configure the repository and dependencies
4. ✅ Automatically connect Rewind to your AI agent (Claude Desktop, Cursor, Windsurf, Zed, or VS Code Roo/Cline)

Or install manually:

```bash
git clone https://github.com/abhinav29102005/rewind.git
cd rewind
uv sync
```

---

## Connect to Your Agent

You can connect Rewind to **any AI agent or IDE** in one command with the interactive integration script:

```bash
./scripts/setup-agent.sh
```

Or target your agent directly:

```bash
./scripts/setup-agent.sh --agent antigravity   # Google Antigravity IDE (Global + Workspace)
./scripts/setup-agent.sh --agent vscode        # VS Code (Extension + Roo/Cline/Copilot)
./scripts/setup-agent.sh --agent cursor          # Cursor global config
./scripts/setup-agent.sh --agent cursor-project  # Current project (.cursor/mcp.json)
./scripts/setup-agent.sh --agent claude          # Claude Desktop
./scripts/setup-agent.sh --agent windsurf        # Windsurf Cascade
./scripts/setup-agent.sh --agent zed             # Zed Editor
./scripts/setup-agent.sh --agent roo             # VS Code Cline / Roo Code
./scripts/setup-agent.sh --agent all             # All detected environments
./scripts/setup-agent.sh --print                 # Print JSON snippet for any client
```

Or using the Python CLI:

```bash
uv run rewind integrate --agent cursor
```

### Manual Configuration Snippets

#### Google Antigravity (AGY)
Add to `~/.gemini/config/mcp_config.json` (Global) or `.agents/mcp_config.json` (Workspace):

```json
{
  "mcpServers": {
    "rewind-guard": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/rewind",
        "run",
        "rewind-mcp"
      ]
    }
  }
}
```

You can also install the approval companion extension:
```bash
antigravity --install-extension vscode-extension/rewind-guard-0.1.0.vsix
```

#### Visual Studio Code (Extension + Roo/Cline)
Install the Rewind Guard VSIX extension:
```bash
code --install-extension vscode-extension/rewind-guard-0.1.0.vsix
```
For Roo Code / Cline MCP, add to `cline_mcp_settings.json`:
```json
{
  "mcpServers": {
    "rewind-guard": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/rewind",
        "run",
        "rewind-mcp"
      ]
    }
  }
}
```

#### Claude Desktop
Add to `~/.config/Claude/claude_desktop_config.json` (Linux) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "rewind-guard": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/rewind",
        "run",
        "rewind-mcp"
      ]
    }
  }
}
```

#### Cursor
Add to `~/.config/Cursor/User/globalStorage/cursor.mcp/config.json` (Linux) or `~/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/config.json` (macOS), or per-project at `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "rewind-guard": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/rewind",
        "run",
        "rewind-mcp"
      ]
    }
  }
}
```

#### Windsurf
Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "rewind-guard": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/rewind",
        "run",
        "rewind-mcp"
      ]
    }
  }
}
```

#### Zed Editor
Add to `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "rewind-guard": {
      "command": {
        "path": "uv",
        "args": ["--directory", "/absolute/path/to/rewind", "run", "rewind-mcp"]
      }
    }
  }
}
```

---

## How It Works

Rewind runs as a local **MCP (Model Context Protocol) server** that acts as an enforceable gate between your agent and your system.

```
AI Agent (Cursor/Claude/etc.) ──► Rewind MCP Proxy ──► Classifier Engine
                                        │                     │
                                        │       [SAFE]        ├─► Execute & log
                                        │       [REVERSIBLE]  ├─► Git Snapshot ──► Execute & log
                                        │       [IRREVERSIBLE]└─► BLOCK ──► Prompt in chat
                                        │                                        │
                                  Credential Broker                    User approves in chat
                               (agent never sees secrets)                        │
                                                                           Execute & seal WAL
```

### In-Chat Approval Flow (No Separate UI Needed)

When your agent attempts a dangerous action (e.g. `DROP TABLE`, `rm -rf`, `docker system prune`, `git push --force`):

1. **Rewind intercepts the call:** Halts execution in under 82ms.
2. **Agent prompts you in the chat:** *"Rewind blocked this action because: Recursive directory deletion. Would you like to approve request `apr_9f81a`?"*
3. **You reply in chat:** *"Yes"*
4. **Agent calls approval tool:** Rewind verifies cryptographic signature, executes the action, and seals the result into an append-only SHA-256 WAL audit log.

---

## MCP Tools Reference

Rewind exposes 5 standard MCP tools on stdio transport:

| Tool | Parameters | Description |
|---|---|---|
| `execute_command` | `command: str`, `session_id?: str` | Runs a command through the guardrail classifier. Safe commands execute immediately; reversible commands create a shadow snapshot first; irreversible commands block and return an approval request ID. |
| `approve_request` | `request_id: str` | Unlocks a blocked destructive action. Can be triggered directly by the user approving in chat. |
| `execute_approved_command` | `request_id: str` | Executes an approved action. Validates cryptographic action payload hash to guarantee the command was not altered. |
| `preview_rollback` | `snapshot_id: str` | Generates a unified git diff showing exactly what changes will be reverted. |
| `rollback_snapshot` | `snapshot_id: str` | Performs instant one-click rollback of the filesystem to the pre-action snapshot. |

---

## Built-In Policy Packs

Rewind ships with production-tested rule classifiers:

| Domain | Matched Patterns | Risk Level | Protection |
|---|---|---|---|
| **Filesystem** | `rm -rf`, `shred`, `dd`, `truncate`, `chmod 777` | Reversible / Irreversible | Shadow commit or full halt |
| **Database (SQL)** | `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, `DELETE` without `WHERE` | Irreversible | Human approval required |
| **Git** | `git push --force`, `git reset --hard`, branch delete | Irreversible | Multi-party consensus gate |
| **Cloud Ops** | `aws ec2 terminate`, `terraform destroy`, bucket delete | Irreversible | Token brokering & block |
| **Containers** | `docker rm -f`, `docker system prune -af` | Irreversible | Block and audit trace |

Test any command against the policy engine from your terminal:

```bash
uv run rewind policy test --tool shell "rm -rf /"
# → Risk: IRREVERSIBLE
# → Reason: Recursive directory deletion

uv run rewind policy test --tool shell "docker system prune -af"
# → Risk: IRREVERSIBLE
# → Reason: System prune removes all unused containers and volumes
```

---

## CLI Reference

```bash
uv run rewind --help                    # Show all commands
uv run rewind-mcp                       # Start the MCP guardrail server on stdio
uv run rewind integrate                 # Agent incorporation wizard
uv run rewind integrate --agent cursor  # Connect Cursor directly
uv run rewind policy list               # List loaded policy packs & rules
uv run rewind policy test "rm -rf /"    # Test classification of any statement
uv run rewind log                       # View tamper-evident audit ledger
uv run rewind verify                    # Verify SHA-256 hash chain integrity
uv run rewind rollback <snapshot_id>    # Restore state from a checkpoint
uv run rewind session start             # Start a tracked team session
uv run rewind start                     # Launch local control plane web server
```

---

## Web Interface

Rewind includes a landing page and interactive simulator built with React, Vite, and Lucide icons:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` to:
- Test real incident simulations interactively
- Review benchmark latency numbers (<82ms intercept, <13ms shadow capture)
- Copy integration snippets with 1-click
- Download `install.sh` and run agent incorporation

---

## Project Structure

```
rewind/
├── src/rewind/
│   ├── classifier/            # AST parsers & regex rule engine
│   ├── policy/                # Policy pack definitions (YAML + Python)
│   ├── proxy/                 # Shell and tool execution interceptors
│   ├── audit/                 # SQLite WAL tamper-evident SHA-256 ledger
│   ├── approval/              # Multi-party consensus & queue management
│   ├── rollback/              # Git shadow tree snapshotting engine
│   ├── mcp_server.py          # FastMCP server implementation
│   └── cli.py                 # Click CLI interface
├── scripts/
│   ├── setup-agent.sh         # Universal agent incorporation script
│   └── generate_config_docs.py# Config schema generator
├── install.sh                 # One-command installer (curl | bash)
├── frontend/                  # Modern documentation & simulation web app
└── tests/                     # Comprehensive test suite
```

---

## Contributing

We welcome contributions! Whether it's new policy packs, agent adapters, or performance enhancements:

```bash
git clone https://github.com/abhinav29102005/rewind.git
cd rewind
uv sync
uv run pytest                  # Run all tests
uv run ruff check src/         # Code quality check
```

---

## License

Apache-2.0

<p align="center">
  <i>Turning 9-second catastrophic deletions into safe, recoverable events.</i>
</p>
