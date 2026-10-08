#!/usr/bin/env bash
# ============================================================================
#  Rewind Agent Integrator
#  Easily connect Rewind MCP guardrails into any AI agent or IDE:
#  - Google Antigravity (AGY / Antigravity IDE)
#  - Visual Studio Code (Extension + Cline / Roo-Code / Copilot)
#  - Claude Desktop
#  - Cursor
#  - Windsurf
#  - Zed Editor
#  - Custom JSON configuration / Print snippet
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

info()    { echo -e "  ${BLUE}ℹ${NC}  $1"; }
success() { echo -e "  ${GREEN}✔${NC}  $1"; }
warn()    { echo -e "  ${YELLOW}⚠${NC}  $1"; }
fail()    { echo -e "  ${RED}✖${NC}  $1"; exit 1; }

# Locate uv or python
UV_PATH="$(command -v uv 2>/dev/null || true)"

if [[ -z "$UV_PATH" ]]; then
  if [[ -x "$HOME/.local/bin/uv" ]]; then
    UV_PATH="$HOME/.local/bin/uv"
  elif [[ -x "$HOME/.cargo/bin/uv" ]]; then
    UV_PATH="$HOME/.cargo/bin/uv"
  fi
fi

OS="$(uname -s)"

# Construct MCP config snippet
get_mcp_snippet() {
  if [[ -n "$UV_PATH" ]]; then
    cat <<SNIPPET
{
  "mcpServers": {
    "rewind-guard": {
      "command": "$UV_PATH",
      "args": [
        "--directory",
        "$REPO_DIR",
        "run",
        "rewind-mcp"
      ]
    }
  }
}
SNIPPET
  else
    cat <<SNIPPET
{
  "mcpServers": {
    "rewind-guard": {
      "command": "python3",
      "args": [
        "-m",
        "rewind.mcp_server"
      ],
      "env": {
        "PYTHONPATH": "$REPO_DIR/src"
      }
    }
  }
}
SNIPPET
  fi
}

merge_mcp_config() {
  local target_file="$1"
  local agent_name="$2"
  local is_zed="${3:-false}"

  mkdir -p "$(dirname "$target_file")"

  if [[ ! -f "$target_file" ]] || [[ ! -s "$target_file" ]]; then
    if [[ "$is_zed" == "true" ]]; then
      cat > "$target_file" <<ZEDEOF
{
  "context_servers": {
    "rewind-guard": {
      "command": {
        "path": "${UV_PATH:-python3}",
        "args": ["--directory", "$REPO_DIR", "run", "rewind-mcp"]
      }
    }
  }
}
ZEDEOF
    else
      get_mcp_snippet > "$target_file"
    fi
    success "Created configuration for ${BOLD}${agent_name}${NC} at: $target_file"
    return
  fi

  # Merge into existing JSON safely using Python
  python3 -c "
import json, sys

path = '$target_file'
is_zed = ('$is_zed' == 'true')
uv_cmd = '${UV_PATH:-python3}'
repo_dir = '$REPO_DIR'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        data = json.loads(content) if content else {}
except Exception:
    data = {}

if is_zed:
    if 'context_servers' not in data or not isinstance(data['context_servers'], dict):
        data['context_servers'] = {}
    data['context_servers']['rewind-guard'] = {
        'command': {
            'path': uv_cmd,
            'args': ['--directory', repo_dir, 'run', 'rewind-mcp']
        }
    }
else:
    if 'mcpServers' not in data or not isinstance(data['mcpServers'], dict):
        data['mcpServers'] = {}
    data['mcpServers']['rewind-guard'] = {
        'command': uv_cmd,
        'args': ['--directory', repo_dir, 'run', 'rewind-mcp']
    }

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
" 2>/dev/null && success "Updated configuration for ${BOLD}${agent_name}${NC} at: $target_file" || {
    warn "Failed to parse $target_file as JSON. Here is the configuration to add manually:"
    get_mcp_snippet
  }
}

install_vsix_if_possible() {
  local vsix_path="$REPO_DIR/vscode-extension/rewind-guard-0.1.0.vsix"
  if [[ -f "$vsix_path" ]]; then
    if command -v antigravity &>/dev/null; then
      antigravity --install-extension "$vsix_path" 2>/dev/null && success "Installed Rewind Guard extension into Antigravity IDE!" || true
    fi
    if command -v code &>/dev/null; then
      code --install-extension "$vsix_path" 2>/dev/null && success "Installed Rewind Guard extension into VS Code!" || true
    fi
  fi
}

detect_paths() {
  # Antigravity paths
  ANTIGRAVITY_GLOBAL="$HOME/.gemini/config/mcp_config.json"
  ANTIGRAVITY_WS="$REPO_DIR/.agents/mcp_config.json"

  if [[ "$OS" == "Darwin" ]]; then
    CLAUDE_CONF="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    CURSOR_GLOBAL="$HOME/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/config.json"
    CODE_ROO="$HOME/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json"
    VSCODE_COPILOT="$HOME/Library/Application Support/Code/User/globalStorage/github.copilot-chat/mcp_config.json"
  else
    CLAUDE_CONF="${XDG_CONFIG_HOME:-$HOME/.config}/Claude/claude_desktop_config.json"
    CURSOR_GLOBAL="${XDG_CONFIG_HOME:-$HOME/.config}/Cursor/User/globalStorage/cursor.mcp/config.json"
    CODE_ROO="${XDG_CONFIG_HOME:-$HOME/.config}/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json"
    VSCODE_COPILOT="${XDG_CONFIG_HOME:-$HOME/.config}/Code/User/globalStorage/github.copilot-chat/mcp_config.json"
  fi
  WINDSURF_CONF="$HOME/.codeium/windsurf/mcp_config.json"
  ZED_CONF="${XDG_CONFIG_HOME:-$HOME/.config}/zed/settings.json"
  PROJECT_CURSOR="$REPO_DIR/.cursor/mcp.json"
}

banner() {
  echo ""
  echo -e "${CYAN}${BOLD}"
  echo "   ┌─────────────────────────────────────────────────────────┐"
  echo "   │   🔄  REWIND — Connect AI Agent Guardrails Proxy        │"
  echo "   └─────────────────────────────────────────────────────────┘"
  echo -e "${NC}"
  echo -e "   ${DIM}Repository path: ${REPO_DIR}${NC}"
  if [[ -n "$UV_PATH" ]]; then
    echo -e "   ${DIM}Runner tool:     ${UV_PATH}${NC}"
  fi
  echo ""
}

print_help() {
  banner
  echo -e "${BOLD}Usage:${NC}"
  echo "  $0 [options]"
  echo ""
  echo -e "${BOLD}Options:${NC}"
  echo "  --agent <name>       Target agent to configure:"
  echo "                       antigravity | vscode | claude | cursor | cursor-project | windsurf | roo | zed | all"
  echo "  --config <path>      Inject rewind-guard config into a custom JSON file path"
  echo "  --print              Print the MCP JSON snippet to stdout and exit"
  echo "  --help, -h           Show this help message"
  echo ""
  echo -e "${BOLD}Examples:${NC}"
  echo "  $0 --agent antigravity"
  echo "  $0 --agent vscode"
  echo "  $0 --agent cursor"
  echo "  $0 --agent all"
  echo "  $0 --print"
  echo ""
}

detect_paths

# Parse flags
TARGET_AGENT=""
CUSTOM_CONFIG=""
PRINT_ONLY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent)
      TARGET_AGENT="$2"
      shift 2
      ;;
    --config)
      CUSTOM_CONFIG="$2"
      shift 2
      ;;
    --print)
      PRINT_ONLY=true
      shift
      ;;
    --help|-h)
      print_help
      exit 0
      ;;
    *)
      warn "Unknown option: $1"
      print_help
      exit 1
      ;;
  esac
done

if [[ "$PRINT_ONLY" == "true" ]]; then
  get_mcp_snippet
  exit 0
fi

if [[ -n "$CUSTOM_CONFIG" ]]; then
  banner
  info "Configuring custom path: $CUSTOM_CONFIG"
  merge_mcp_config "$CUSTOM_CONFIG" "Custom MCP Client"
  echo ""
  success "Done! Your agent will now route commands through Rewind."
  exit 0
fi

# Direct agent flag passed
if [[ -n "$TARGET_AGENT" ]]; then
  banner
  case "$TARGET_AGENT" in
    antigravity|agy)
      merge_mcp_config "$ANTIGRAVITY_GLOBAL" "Antigravity IDE (Global)"
      merge_mcp_config "$ANTIGRAVITY_WS" "Antigravity Workspace (.agents)"
      install_vsix_if_possible
      info "Antigravity IDE will immediately load Rewind MCP guardrails."
      ;;
    vscode)
      merge_mcp_config "$CODE_ROO" "VS Code (Roo/Cline MCP)"
      merge_mcp_config "$VSCODE_COPILOT" "VS Code Copilot MCP"
      install_vsix_if_possible
      info "VS Code extensions and MCP tools are now connected."
      ;;
    claude)
      merge_mcp_config "$CLAUDE_CONF" "Claude Desktop"
      info "Restart Claude Desktop to activate the Rewind guard."
      ;;
    cursor)
      merge_mcp_config "$CURSOR_GLOBAL" "Cursor (Global)"
      info "Restart Cursor to activate the Rewind guard."
      ;;
    cursor-project)
      merge_mcp_config "$PROJECT_CURSOR" "Cursor (Project-level)"
      info "Cursor will automatically pick up this project's .cursor/mcp.json."
      ;;
    windsurf)
      merge_mcp_config "$WINDSURF_CONF" "Windsurf Cascade"
      info "Restart Windsurf to activate the Rewind guard."
      ;;
    roo|cline)
      merge_mcp_config "$CODE_ROO" "VS Code Roo Code / Cline"
      info "Roo Code / Cline will immediately recognize rewind-guard."
      ;;
    zed)
      merge_mcp_config "$ZED_CONF" "Zed Editor" true
      info "Restart Zed or reload context servers."
      ;;
    all)
      info "Configuring all detected environments..."
      merge_mcp_config "$ANTIGRAVITY_GLOBAL" "Antigravity IDE (Global)"
      merge_mcp_config "$ANTIGRAVITY_WS" "Antigravity Workspace (.agents)"
      merge_mcp_config "$CLAUDE_CONF" "Claude Desktop"
      merge_mcp_config "$CURSOR_GLOBAL" "Cursor (Global)"
      merge_mcp_config "$PROJECT_CURSOR" "Cursor (Project-level)"
      merge_mcp_config "$WINDSURF_CONF" "Windsurf"
      merge_mcp_config "$CODE_ROO" "VS Code Roo / Cline"
      merge_mcp_config "$ZED_CONF" "Zed Editor" true
      install_vsix_if_possible
      success "Configured all available environments!"
      ;;
    *)
      fail "Unknown agent: $TARGET_AGENT. Valid: antigravity, vscode, claude, cursor, cursor-project, windsurf, roo, zed, all"
      ;;
  esac
  exit 0
fi

# Interactive mode
banner
echo -e "  ${BOLD}Select your AI Agent / Environment to connect:${NC}"
echo ""
echo -e "    ${CYAN}1)${NC} Antigravity IDE (AGY) ${DIM}($ANTIGRAVITY_GLOBAL)${NC}"
echo -e "    ${CYAN}2)${NC} VS Code (VSIX + MCP)  ${DIM}(Extension & Roo/Cline)${NC}"
echo -e "    ${CYAN}3)${NC} Claude Desktop        ${DIM}($CLAUDE_CONF)${NC}"
echo -e "    ${CYAN}4)${NC} Cursor (Global)       ${DIM}($CURSOR_GLOBAL)${NC}"
echo -e "    ${CYAN}5)${NC} Cursor (Project)      ${DIM}($PROJECT_CURSOR)${NC}"
echo -e "    ${CYAN}6)${NC} Windsurf              ${DIM}($WINDSURF_CONF)${NC}"
echo -e "    ${CYAN}7)${NC} Zed Editor            ${DIM}($ZED_CONF)${NC}"
echo -e "    ${CYAN}8)${NC} Connect ALL of the above"
echo -e "    ${CYAN}9)${NC} Print MCP JSON snippet (Copy & Paste)"
echo ""

read -rp "  Select [1-9]: " CHOICE
echo ""

case "${CHOICE:-9}" in
  1)
    merge_mcp_config "$ANTIGRAVITY_GLOBAL" "Antigravity IDE (Global)"
    merge_mcp_config "$ANTIGRAVITY_WS" "Antigravity Workspace (.agents)"
    install_vsix_if_possible
    info "Antigravity IDE is now protected by Rewind."
    ;;
  2)
    merge_mcp_config "$CODE_ROO" "VS Code Roo / Cline"
    merge_mcp_config "$VSCODE_COPILOT" "VS Code Copilot MCP"
    install_vsix_if_possible
    info "VS Code is now protected by Rewind."
    ;;
  3)
    merge_mcp_config "$CLAUDE_CONF" "Claude Desktop"
    info "Restart Claude Desktop to activate the Rewind guard."
    ;;
  4)
    merge_mcp_config "$CURSOR_GLOBAL" "Cursor (Global)"
    info "Restart Cursor to activate the Rewind guard."
    ;;
  5)
    merge_mcp_config "$PROJECT_CURSOR" "Cursor (Project-level)"
    info "Cursor will automatically pick up this project's .cursor/mcp.json."
    ;;
  6)
    merge_mcp_config "$WINDSURF_CONF" "Windsurf Cascade"
    info "Restart Windsurf to activate the Rewind guard."
    ;;
  7)
    merge_mcp_config "$ZED_CONF" "Zed Editor" true
    info "Restart Zed or reload context servers."
    ;;
  8)
    info "Configuring all environments..."
    merge_mcp_config "$ANTIGRAVITY_GLOBAL" "Antigravity IDE (Global)"
    merge_mcp_config "$ANTIGRAVITY_WS" "Antigravity Workspace (.agents)"
    merge_mcp_config "$CLAUDE_CONF" "Claude Desktop"
    merge_mcp_config "$CURSOR_GLOBAL" "Cursor (Global)"
    merge_mcp_config "$PROJECT_CURSOR" "Cursor (Project-level)"
    merge_mcp_config "$WINDSURF_CONF" "Windsurf"
    merge_mcp_config "$CODE_ROO" "VS Code Roo / Cline"
    merge_mcp_config "$ZED_CONF" "Zed Editor" true
    install_vsix_if_possible
    success "All environments configured successfully!"
    ;;
  9)
    echo -e "  ${BOLD}Add this block to your agent's MCP config file:${NC}"
    echo ""
    get_mcp_snippet
    echo ""
    ;;
  *)
    warn "Invalid option. Exiting."
    exit 1
    ;;
esac

echo ""
echo -e "  ${GREEN}${BOLD}✔ Done! Your AI agent is now protected by Rewind.${NC}"
echo -e "  ${DIM}Every destructive command will be intercepted for approval directly in chat.${NC}"
echo ""
