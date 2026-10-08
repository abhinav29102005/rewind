# Rewind Agent Guardrails

You use AI agents (like Cursor, Claude Code, or Antigravity) to write code and execute commands. **Rewind** is an enforced safety layer that intercepts their actions, ensuring they cannot make irreversible mistakes (like dropping production databases or deleting repositories) without your cryptographic approval.

This VS Code extension provides the Human-in-the-Loop (HITL) approval UI directly inside your editor. 

It is a thin client over the local [Rewind](https://github.com/abhinav29102005/rewind) engine.

## What it does

When your AI agent connects to the Rewind MCP Server or Shell Proxy, its actions are classified:
*   **Safe Actions** (`ls`, `git status`) execute immediately.
*   **Reversible Actions** (`UPDATE`, file modifications) trigger an automatic snapshot before executing.
*   **Irreversible Actions** (`DROP TABLE`, `rm -rf`) are **physically blocked** by the proxy.

When an action is blocked, the agent is halted. You can then use this extension to review the blocked action and either **Approve** or **Deny** it.

## Commands

| Command | Action |
| :--- | :--- |
| `Rewind: Approve Action` | Generate a cryptographic token to allow a blocked agent action to execute once. |
| `Rewind: Deny Action` | Hard-reject the agent's request, forcing it to try another approach. |

## Requirements

This extension requires the Rewind Python engine to be running locally. 
Install it via your Python package manager:
```bash
uv pip install rewind-guard
```

Then, run the MCP server so your agents can connect:
```bash
uv run rewind-mcp
```

## How it works
When you approve a request via the Command Palette, this extension communicates with your local Rewind Approval Queue. If approved, Rewind generates an HMAC-signed approval code and unblocks the agent's specific tool call.

## License
Apache-2.0
