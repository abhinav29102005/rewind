# Integrating Rewind with Cursor

> Add Rewind as an MCP server to Cursor so every destructive action by the AI agent is intercepted and requires your approval — right inside the chat.

## Prerequisites

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) package manager
- Rewind installed (`bash install.sh` or `uv pip install -e .`)
- Cursor IDE installed

## Automatic Setup (Recommended)

```bash
bash install.sh
# Select option 2 → Cursor
```

## Manual Setup

### 1. Locate your MCP config

| OS    | Path |
|-------|------|
| macOS | `~/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/config.json` |
| Linux | `~/.config/Cursor/User/globalStorage/cursor.mcp/config.json` |

### 2. Add Rewind

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

### 3. Restart Cursor

Restart the IDE. The Rewind tools will be available to Cursor's agent mode.

## How It Works

When the Cursor agent tries to run a destructive shell command:

1. Rewind intercepts and classifies the action
2. If **irreversible**, the agent is blocked and told to ask you for approval in the chat
3. You reply with "yes" or "approve" — the agent calls `approve_request` and proceeds
4. If **reversible**, a git snapshot is taken first so you can `rollback_snapshot` if needed
5. If **safe**, the command runs immediately

All actions are recorded in the tamper-evident audit log.

## Per-Project Configuration

You can also add a `.cursor/mcp.json` file to any project root for project-scoped MCP servers:

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

This way Rewind only activates for specific projects.
