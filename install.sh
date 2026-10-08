#!/usr/bin/env bash
# ============================================================================
#  Rewind — One-Command Installer
#  Installs rewind-guard and optionally configures it for your AI agent.
#
#  Usage:
#    curl -fsSL https://raw.githubusercontent.com/abhinav29102005/rewind/main/install.sh | bash
#    # or locally:
#    bash install.sh
# ============================================================================

set -euo pipefail

# -- Colors ------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

banner() {
  echo ""
  echo -e "${CYAN}${BOLD}"
  echo "  ██████╗ ███████╗██╗    ██╗██╗███╗   ██╗██████╗ "
  echo "  ██╔══██╗██╔════╝██║    ██║██║████╗  ██║██╔══██╗"
  echo "  ██████╔╝█████╗  ██║ █╗ ██║██║██╔██╗ ██║██║  ██║"
  echo "  ██╔══██╗██╔══╝  ██║███╗██║██║██║╚██╗██║██║  ██║"
  echo "  ██║  ██║███████╗╚███╔███╔╝██║██║ ╚████║██████╔╝"
  echo "  ╚═╝  ╚═╝╚══════╝ ╚══╝╚══╝ ╚═╝╚═╝  ╚═══╝╚═════╝ "
  echo -e "${NC}"
  echo -e "  ${DIM}Enforced approval & undo layer for AI agents${NC}"
  echo ""
}

info()    { echo -e "  ${BLUE}ℹ${NC}  $1"; }
success() { echo -e "  ${GREEN}✔${NC}  $1"; }
warn()    { echo -e "  ${YELLOW}⚠${NC}  $1"; }
fail()    { echo -e "  ${RED}✖${NC}  $1"; exit 1; }
step()    { echo -e "\n  ${BOLD}[$1/$TOTAL_STEPS]${NC} $2"; }

TOTAL_STEPS=5

# ============================================================================
# STEP 0 — Detect OS and Architecture
# ============================================================================
banner

OS="$(uname -s)"
ARCH="$(uname -m)"
info "Detected: ${BOLD}$OS${NC} ($ARCH)"

if [[ "$OS" != "Linux" && "$OS" != "Darwin" ]]; then
  fail "Unsupported OS: $OS. Rewind supports Linux and macOS."
fi

# ============================================================================
# STEP 1 — Check Python >= 3.11
# ============================================================================
step 1 "Checking Python version..."

PYTHON=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3 python; do
  if command -v "$candidate" &>/dev/null; then
    ver=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
    major="${ver%%.*}"
    minor="${ver##*.}"
    if [[ "$major" -ge 3 && "$minor" -ge 11 ]]; then
      PYTHON="$candidate"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  fail "Python >= 3.11 is required. Install it from https://python.org and re-run."
fi
success "Using $($PYTHON --version) at $(command -v $PYTHON)"

# ============================================================================
# STEP 2 — Install uv (if missing)
# ============================================================================
step 2 "Checking for uv package manager..."

if command -v uv &>/dev/null; then
  success "uv is already installed ($(uv --version))"
else
  info "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  if command -v uv &>/dev/null; then
    success "uv installed successfully ($(uv --version))"
  else
    fail "Failed to install uv. Install manually: https://docs.astral.sh/uv/"
  fi
fi

# ============================================================================
# STEP 3 — Clone or use existing repo
# ============================================================================
step 3 "Setting up Rewind source..."

REWIND_DIR=""

if [[ -f "pyproject.toml" ]] && grep -q "rewind-guard" pyproject.toml 2>/dev/null; then
  REWIND_DIR="$(pwd)"
  success "Using existing Rewind project at $REWIND_DIR"
else
  INSTALL_DIR="${REWIND_INSTALL_DIR:-$HOME/.rewind}"
  if [[ -d "$INSTALL_DIR" && -f "$INSTALL_DIR/pyproject.toml" ]]; then
    REWIND_DIR="$INSTALL_DIR"
    info "Updating existing installation at $REWIND_DIR..."
    (cd "$REWIND_DIR" && git pull --quiet 2>/dev/null || true)
    success "Updated Rewind at $REWIND_DIR"
  else
    info "Cloning Rewind to $INSTALL_DIR..."
    git clone --quiet https://github.com/abhinav29102005/rewind.git "$INSTALL_DIR"
    REWIND_DIR="$INSTALL_DIR"
    success "Cloned to $REWIND_DIR"
  fi
fi

# ============================================================================
# STEP 4 — Install dependencies & package
# ============================================================================
step 4 "Installing rewind-guard and dependencies..."

cd "$REWIND_DIR"
uv sync --quiet 2>/dev/null || uv pip install -e ".[dev]" --quiet
success "rewind-guard installed"

# Verify the CLI works
if uv run rewind --help &>/dev/null; then
  success "CLI verified: 'uv run rewind' is working"
else
  warn "CLI not responding — you may need to run 'uv sync' manually"
fi

# ============================================================================
# STEP 5 — Configure MCP Server for your agent
# ============================================================================
step 5 "Configuring MCP Server for your AI agent..."

echo ""
echo -e "  ${BOLD}Which AI agent do you want to connect Rewind to?${NC}"
echo ""
echo -e "    ${CYAN}1${NC}) Claude Desktop"
echo -e "    ${CYAN}2${NC}) Cursor"
echo -e "    ${CYAN}3${NC}) Windsurf"
echo -e "    ${CYAN}4${NC}) Manual / Other (print config only)"
echo -e "    ${CYAN}5${NC}) Skip (configure later)"
echo ""
read -rp "  Select [1-5]: " AGENT_CHOICE
echo ""

UV_PATH="$(command -v uv)"

MCP_JSON=$(cat <<MCPEOF
{
  "mcpServers": {
    "rewind-guard": {
      "command": "$UV_PATH",
      "args": [
        "--directory",
        "$REWIND_DIR",
        "run",
        "rewind-mcp"
      ]
    }
  }
}
MCPEOF
)

write_config() {
  local target_file="$1"
  local agent_name="$2"

  if [[ -f "$target_file" ]]; then
    $PYTHON -c "
import json
target = '$target_file'
rewind_dir = '$REWIND_DIR'
uv_path = '$UV_PATH'

with open(target, 'r') as f:
    try:
        data = json.load(f)
    except json.JSONDecodeError:
        data = {}

if 'mcpServers' not in data:
    data['mcpServers'] = {}

data['mcpServers']['rewind-guard'] = {
    'command': uv_path,
    'args': ['--directory', rewind_dir, 'run', 'rewind-mcp']
}

with open(target, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
"
  else
    mkdir -p "$(dirname "$target_file")"
    echo "$MCP_JSON" > "$target_file"
  fi

  success "Configured ${agent_name} at ${target_file}"
}

case "${AGENT_CHOICE:-5}" in
  1)
    if [[ "$OS" == "Darwin" ]]; then
      CONFIG_FILE="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    else
      CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/Claude/claude_desktop_config.json"
    fi
    write_config "$CONFIG_FILE" "Claude Desktop"
    info "Restart Claude Desktop to load the Rewind MCP server."
    ;;
  2)
    if [[ "$OS" == "Darwin" ]]; then
      CONFIG_FILE="$HOME/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/config.json"
    else
      CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/Cursor/User/globalStorage/cursor.mcp/config.json"
    fi
    write_config "$CONFIG_FILE" "Cursor"
    info "Restart Cursor to load the Rewind MCP server."
    ;;
  3)
    CONFIG_FILE="$HOME/.codeium/windsurf/mcp_config.json"
    write_config "$CONFIG_FILE" "Windsurf"
    info "Restart Windsurf to load the Rewind MCP server."
    ;;
  4)
    echo -e "  ${BOLD}Add this to your agent's MCP configuration:${NC}"
    echo ""
    echo "$MCP_JSON"
    echo ""
    ;;
  5)
    info "Skipped. Run 'bash install.sh' again to configure later."
    ;;
  *)
    warn "Invalid choice. Skipping configuration."
    ;;
esac

# ============================================================================
# Done!
# ============================================================================
echo ""
echo -e "  ${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${GREEN}${BOLD}  ✔  Rewind is installed and ready!${NC}"
echo -e "  ${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BOLD}Quick commands:${NC}"
echo ""
echo -e "    ${CYAN}uv run rewind --help${NC}          Show all CLI commands"
echo -e "    ${CYAN}uv run rewind-mcp${NC}             Start the MCP guardrail server"
echo -e "    ${CYAN}uv run rewind policy list${NC}     Show loaded policy packs"
echo -e "    ${CYAN}uv run rewind policy test${NC}     Test a command classification"
echo ""
echo -e "  ${BOLD}Test it out:${NC}"
echo ""
echo -e "    ${DIM}\$ uv run rewind policy test --tool shell \"rm -rf /\"${NC}"
echo -e "    ${RED}Risk: IRREVERSIBLE${NC}"
echo -e "    ${DIM}Reason: Recursive directory deletion${NC}"
echo ""
echo -e "  ${DIM}Docs: https://github.com/abhinav29102005/rewind${NC}"
echo ""
