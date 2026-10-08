# Integrating Rewind with Claude Desktop

> Connect Rewind as an MCP server to Claude Desktop so every dangerous action your AI takes is intercepted, reviewed, and approved — directly in the chat window.

## Prerequisites

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) package manager
- Rewind installed (`bash install.sh` or `uv pip install -e .` from the repo)
- Claude Desktop installed

## Automatic Setup (Recommended)

Run the installer and select **Claude Desktop** when prompted:

```bash
bash install.sh
# Select option 1 → Claude Desktop
```

The installer will automatically write the correct config to your system's `claude_desktop_config.json`.

## Manual Setup

### 1. Locate your config file

| OS    | Path |
|-------|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### 2. Add the Rewind MCP server

Open the file and add (or merge) the `rewind-guard` entry under `mcpServers`:

```json
{
  "mcpServers": {
    "rewind-guard": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/rewind",
        "run",
        "rewind-mcp"
      ]
    }
  }
}
```

Replace `/path/to/uv` with the output of `which uv` and `/path/to/rewind` with the absolute path to the cloned Rewind repository.

### 3. Restart Claude Desktop

Close and re-open Claude Desktop. You should see the Rewind tools appear in the available MCP tools list.

## Available Tools

Once connected, Claude will have access to these guarded tools:

| Tool | Description |
|------|-------------|
| `execute_command` | Run a shell command through the Rewind guardrail pipeline |
| `approve_request` | Approve a blocked action directly in chat |
| `execute_approved_command` | Execute a previously approved action |
| `preview_rollback` | Preview the diff for a snapshot before restoring |
| `rollback_snapshot` | Restore filesystem state to a checkpoint |

## How It Works in Practice

1. **You ask Claude to do something dangerous** (e.g., "delete all `.log` files recursively")
2. **Rewind classifies the action** as `IRREVERSIBLE` based on policy rules
3. **Claude tells you the action was blocked** and asks for your permission directly in the chat
4. **You reply "yes" or "approve"** in the chat
5. **Claude calls `approve_request`** and then executes the action safely
6. **Everything is logged** in the tamper-evident audit trail

If the action is `REVERSIBLE`, Rewind takes a snapshot first, executes the command, and gives Claude a rollback handle in case anything goes wrong.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tools don't appear in Claude | Restart Claude Desktop; check the config file path matches your OS |
| "command not found: uv" | Use the full absolute path to `uv` in the config (run `which uv`) |
| Permission errors on audit.db | Ensure the Rewind data directory is writable |
| Python version error | Rewind requires Python ≥ 3.11 |
