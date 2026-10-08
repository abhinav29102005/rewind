# Integrating Rewind with Any MCP-Compatible Client

Rewind runs as a standard MCP (Model Context Protocol) server. Any agent or client that supports MCP can connect to it.

## Quick Reference

| Detail | Value |
|--------|-------|
| Server name | `Rewind Guardrails Proxy` |
| Entry point | `rewind-mcp` (registered in `pyproject.toml`) |
| Transport | stdio (standard MCP transport) |
| Tools exposed | `execute_command`, `approve_request`, `execute_approved_command`, `preview_rollback`, `rollback_snapshot` |

## Generic MCP Configuration

```json
{
  "mcpServers": {
    "rewind-guard": {
      "command": "/absolute/path/to/uv",
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

## Running Standalone (for testing)

```bash
cd /path/to/rewind
uv run rewind-mcp
```

The server will start on stdio transport and wait for MCP protocol messages.

## Tool Reference

### `execute_command(command, session_id?)`
Execute a shell command through the guardrail pipeline. Classifies the command as safe/reversible/irreversible and acts accordingly.

### `approve_request(request_id)`
Approve a previously blocked destructive action. Returns confirmation and unlocks the action for execution.

### `execute_approved_command(request_id)`
Execute a command that was previously blocked and has been approved. Verifies cryptographic action hash integrity before execution.

### `preview_rollback(snapshot_id)`
Show the file diff that would be restored if rolling back to a specific snapshot.

### `rollback_snapshot(snapshot_id)`
Restore the filesystem state to a pre-action checkpoint.

## Policy Customization

Rewind ships with policy packs for:
- **Filesystem** (`rm -rf`, `shred`, etc.)
- **PostgreSQL** (`DROP TABLE`, `TRUNCATE`, etc.)
- **Git** (`git push --force`, `git reset --hard`, etc.)
- **AWS S3** (`s3 rm --recursive`, bucket deletion, etc.)
- **Docker** (`docker rm`, `docker system prune`, etc.)

List loaded policies:
```bash
uv run rewind policy list
```

Test a command classification:
```bash
uv run rewind policy test --tool shell "rm -rf /"
# → Risk: IRREVERSIBLE
# → Reason: Recursive directory deletion
```
