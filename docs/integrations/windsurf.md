# Integrating Rewind with Windsurf (Codeium)

> Connect Rewind to Windsurf's Cascade agent via MCP to enforce approval gates on dangerous operations.

## Automatic Setup

```bash
bash install.sh
# Select option 3 → Windsurf
```

## Manual Setup

### 1. Config file location

```
~/.codeium/windsurf/mcp_config.json
```

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

### 3. Restart Windsurf

The Rewind tools will appear in the MCP panel.

## Behaviour

Windsurf's Cascade agent will route shell commands through Rewind's `execute_command` tool. Destructive actions are paused and Cascade will ask you for approval directly in the chat.
